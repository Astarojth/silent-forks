#!/usr/bin/env python3
"""Frontier-model probes for ForkDPO.

Give each silent-fork prefix to frontier models in native tool-call format and record the next action,
4 samples per fork per model. Prefixes are read from data/pairs/pairs.jsonl.

Before every request the guard checks recorded spend plus reserves of in-flight requests against
STOP_AT_USD and the model's own cap. Per-model refusal and error breakers stop a misbehaving model.
Requests are rate-limited per model. Results are appended as JSONL under work/probe and the script resumes from them.
"""
import json, os, re, sys, time, glob, math, random, signal, socket, threading, http.client, urllib.request, urllib.error
import concurrent.futures as cf
from collections import Counter, deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('FORKDPO_PROBE_WORK', REPO / 'work' / 'probe'))
PAIRS = REPO / 'data' / 'pairs' / 'pairs.jsonl'
RES = ROOT / 'results'; LOG = ROOT / 'logs'
RES.mkdir(parents=True, exist_ok=True); LOG.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG / 'probe.log'
BREAKERS = RES / 'breakers.json'
_API = os.environ.get('FORKDPO_API_BASE', 'https://api.openai.com/v1').rstrip('/')
CHAT_URL = _API + '/chat/completions'
RESP_URL = _API + '/responses'
CAP_USD, STOP_AT_USD = 200.0, 185.0
UNRECORDED_USD = 0.0
SAMPLES = 4

# Official list prices, USD per 1M tokens (2026-10). DeepSeek uses peak rates as an upper bound.
PRICE = {
    'deepseek-flash':  dict(inp=0.30, cached=0.006, write=0.30, out=1.20),
    'glm-5.3':         dict(inp=1.40, cached=0.26,  write=1.40, out=4.40),
    'claude-opus-5-5': dict(inp=4.00, cached=0.20,  write=5.00, out=20.0),
    'gpt-6.1-sol':     dict(inp=2.00, cached=0.10,  write=2.50, out=10.0),
}
CONCURRENCY = {'deepseek-flash': 16, 'glm-5.3': 8, 'claude-opus-5-5': 8, 'gpt-6.1-sol': 8}
MODELS = list(PRICE)
MAX_OUT = {'deepseek-flash': 393216, 'glm-5.3': 131072, 'claude-opus-5-5': 128000, 'gpt-6.1-sol': 128000}

# Budget guard and breakers. The estimate per call is
# max(default, observed p95). A request also waits while spend + worst case of in-flight requests could pass CAP_USD.
MODEL_CAP_USD = {'claude-opus-5-5': 80.0, 'gpt-6.1-sol': 60.0, 'glm-5.3': 30.0, 'deepseek-flash': 10.0}
DEFAULT_EST_USD = {'claude-opus-5-5': 0.06, 'gpt-6.1-sol': 0.03, 'glm-5.3': 0.015, 'deepseek-flash': 0.003}
WINDOW = 50
REFUSAL_STREAK, REFUSALS_IN_WINDOW = 5, 10
FAIL_STREAK, FAILS_IN_WINDOW, SAME_ERROR_STREAK = 5, 10, 3
BACKOFF = (4, 8, 16)
STALL_SEC = 20 * 60
RPM_LIMIT = dict.fromkeys(MODELS, 50)
REFUSAL_FINISH = {'content_filter', 'refusal'}
REFUSAL_BODY = re.compile(r'content[_ -]?filter|refusal|data_inspection_failed', re.I)
ABORTED = 'aborted'

ACT = re.compile(r'```mswea_bash_command\s*\n(.*?)\n```', re.S)
OBS = re.compile(r'<returncode>(.*?)</returncode>\s*<output>\n?(.*?)\n?</output>', re.S)
SYS_TOOL = ("You are a software engineering agent working in a terminal inside a git repository. "
            "Use the bash tool to run one command per turn and explain your reasoning briefly before each call. "
            "Edit files with shell tools (e.g. `cat <<'EOF' > file`, `sed -i`), and view files with `nl -ba file | sed -n '10,40p'`. "
            "When the task is done, call the bash tool with `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` to end the session.")
TOOL_DESC = "Run a shell command from the repository root. Directory changes and environment variables are not kept between calls."
TOOL_PARAMS = {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
CHAT_TOOLS = [{"type": "function", "function": {"name": "bash", "description": TOOL_DESC, "parameters": TOOL_PARAMS}}]
RESP_TOOL = {"type": "function", "name": "bash", "description": TOOL_DESC, "parameters": TOOL_PARAMS}

lock = threading.RLock()
state = dict(done=0, err=0)
_logf = None
GUARD = None
TERM = []


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def scrub(s):
    k = os.environ.get('FORKDPO_API_KEY')
    return s.replace(k, '***') if k and k in s else s


def log(msg):
    global _logf
    line = f"{now()} {scrub(msg)}"
    with lock:
        if _logf is None: _logf = open(LOG_FILE, 'a')
        _logf.write(line + '\n'); _logf.flush()


# ---------- prompt conversion ----------
def turns(prompt):
    """Yield ('assistant', text, command|None) and ('user', text, (rc, output)|None) from a mini-swe-agent prefix."""
    for m in prompt[1:]:
        if m['role'] == 'assistant':
            a = ACT.search(m['content'])
            yield 'assistant', ACT.sub('', m['content']).strip(), (a.group(1) if a else None)
        else:
            o = OBS.search(m['content'])
            yield 'user', m['content'], ((o.group(1).strip(), o.group(2)) if o else None)


def to_chat(prompt, model=None):
    out = [{"role": "system", "content": SYS_TOOL}]; pending = None; n = 0
    for role, text, extra in turns(prompt):
        if role == 'assistant':
            if extra is None:
                out.append({"role": "assistant", "content": text or "(no command)"}); pending = None
            else:
                n += 1; pending = f"call_{n}"
                out.append({"role": "assistant", "content": text or None,
                            "tool_calls": [{"id": pending, "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": extra})}}]})
            # DeepSeek thinking mode rejects tool-call history without reasoning_content; the 4B prefix has none recorded.
            if model == 'deepseek-flash': out[-1]["reasoning_content"] = ""
            continue
        elif pending:
            body = f"exit code {extra[0]}\n{extra[1]}" if extra else text
            out.append({"role": "tool", "tool_call_id": pending, "content": body}); pending = None
        elif out[-1]['role'] == 'user':
            out[-1]['content'] += '\n\n' + text
        else:
            out.append({"role": "user", "content": text})
    return out


def to_resp(prompt):
    out = []; pending = None; n = 0
    for role, text, extra in turns(prompt):
        if role == 'assistant':
            if text: out.append({"role": "assistant", "content": text})
            if extra is None:
                if not text: out.append({"role": "assistant", "content": "(no command)"})
                pending = None; continue
            n += 1; pending = f"call_{n}"
            out.append({"type": "function_call", "call_id": pending, "name": "bash", "arguments": json.dumps({"command": extra})})
        elif pending:
            body = f"exit code {extra[0]}\n{extra[1]}" if extra else text
            out.append({"type": "function_call_output", "call_id": pending, "output": body}); pending = None
        else:
            out.append({"role": "user", "content": text})
    return out


# ---------- HTTP ----------
def post(url, body, timeout=1800):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['FORKDPO_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


TIMEOUTS = (socket.timeout, TimeoutError)
CONNECTION_ERRORS = (ConnectionError, http.client.HTTPException, urllib.error.URLError)
# Failures after the request was sent, which the provider may still bill; each one is charged as unrecorded spend.
MAYBE_BILLED = TIMEOUTS + (http.client.IncompleteRead, http.client.RemoteDisconnected)


def attempts_allowed(code=None, exc=None, body=''):
    """Max attempts for a failure: 429/5xx/timeouts/connection errors 4, 401/403 2, anything else 1.
    Content-filter and refusal bodies are never retried."""
    if code is not None:
        if REFUSAL_BODY.search(body or ''): return 1
        if code == 429 or 500 <= code < 600: return len(BACKOFF) + 1
        if code in (401, 403): return 2
        return 1
    return len(BACKOFF) + 1 if isinstance(exc, TIMEOUTS + CONNECTION_ERRORS) else 1


class RateLimiter:
    """At most rpm[model] request starts per model in any 60 s window."""

    def __init__(self, rpm, clock=time.monotonic, sleep=time.sleep):
        self.rpm, self.clock, self.sleep = rpm, clock, sleep
        self.lock = threading.Lock(); self.starts = {m: deque() for m in rpm}

    def wait(self, m):
        while True:
            with self.lock:
                t = self.clock(); q = self.starts[m]
                while q and t - q[0] >= 60: q.popleft()
                if len(q) < self.rpm[m]:
                    q.append(t); return
                delay = 60 - (t - q[0])
            self.sleep(delay + 0.05)


RATE = RateLimiter(RPM_LIMIT)


def call_with_retry(fn, label, gate=None, on_billed_failure=None, throttle=None, sleep=time.sleep):
    """Return (response, None) or (None, error). Returns (None, ABORTED) if `gate()` turns false before a retry.
    `throttle()` runs before every retry attempt; the caller throttles the first attempt."""
    for attempt in range(1, len(BACKOFF) + 2):
        if throttle and attempt > 1: throttle()
        try:
            return fn(), None
        except urllib.error.HTTPError as e:
            try: body = e.read().decode(errors='replace')[:300]
            except Exception: body = ''
            err, limit, billed = f"HTTP{e.code}: {body}", attempts_allowed(code=e.code, body=body), e.code in (504, 524)
        except Exception as e:  # timeouts, connection resets, malformed responses
            err, limit, billed = f"{type(e).__name__}: {str(e)[:200]}", attempts_allowed(exc=e), isinstance(e, MAYBE_BILLED)
        if billed and on_billed_failure: on_billed_failure()
        if attempt >= limit: return None, scrub(err)
        sleep(BACKOFF[attempt - 1] + random.random() * 2)
        if gate and not gate(): return None, ABORTED
    return None, 'exhausted'


# ---------- usage & cost ----------
def usage_of(model, d):
    u = d.get('usage') or {}
    if model == 'gpt-6.1-sol':
        inp = u.get('input_tokens', 0); out = u.get('output_tokens', 0)
        cached = (u.get('input_tokens_details') or {}).get('cached_tokens', 0) or 0; write = 0
    else:
        inp = u.get('prompt_tokens', 0); out = u.get('completion_tokens', 0)
        det = u.get('prompt_tokens_details') or {}
        cached = det.get('cached_tokens', 0) or u.get('cache_read_input_tokens', 0) or 0
        write = det.get('cache_creation_tokens', 0) or u.get('cache_creation_input_tokens', 0) or 0
    return dict(inp=inp, out=out, cached=cached, write=write)


def cost_of(model, u):
    p = PRICE[model]
    fresh = max(u['inp'] - u['cached'] - u['write'], 0)
    return (fresh * p['inp'] + u['cached'] * p['cached'] + u['write'] * p['write'] + u['out'] * p['out']) / 1e6


# ---------- outcomes, budget guard, breakers ----------
def is_refusal_error(err):
    return bool(err) and err.startswith('HTTP') and bool(REFUSAL_BODY.search(err))


def outcome(rec):
    """'ok', 'refusal' or 'error'. A refusal is a content_filter/refusal finish, a content-filter HTTP error, or a reply
    with neither a command nor any text."""
    if rec.get('error'): return 'refusal' if is_refusal_error(rec['error']) else 'error'
    if rec.get('finish') in REFUSAL_FINISH: return 'refusal'
    if not rec.get('command') and not (rec.get('text') or '').strip(): return 'refusal'
    return 'ok'


def finished(r):
    """Terminal results are not retried on restart: replies (incl. refusals) and errors already retried once."""
    return r is not None and (not r.get('error') or outcome(r) == 'refusal' or r.get('attempts', 1) >= 2)


def p95(xs):
    if not xs: return 0.0
    s = sorted(xs)
    return s[max(math.ceil(0.95 * len(s)) - 1, 0)]


def worst_case(model, est):
    return est + MAX_OUT[model] * PRICE[model]['out'] / 1e6


def breaker_label(b):
    b = b or {}; st = b.get('state', 'closed')
    return st if st == 'closed' else f"{st}[{b.get('kind', '')}: {b.get('reason', '')}]"


class Guard:
    """Thread-safe budget ledger with in-flight reserves and per-model refusal/error breakers."""

    def __init__(self, path=None, logf=None):
        self.lock = threading.RLock(); self.save_lock = threading.RLock()
        self.path, self.log = (Path(path) if path else None), (logf or (lambda msg: None))
        self.recorded = dict.fromkeys(MODELS, 0.0); self.unrecorded = dict.fromkeys(MODELS, 0.0)
        self.inflight = dict.fromkeys(MODELS, 0.0); self.inflight_worst = dict.fromkeys(MODELS, 0.0)
        self.n_inflight = dict.fromkeys(MODELS, 0)
        self.costs = {m: [] for m in MODELS}; self.est = dict(DEFAULT_EST_USD)
        self.window = {m: deque(maxlen=WINDOW) for m in MODELS}
        self.counts = {m: Counter() for m in MODELS}
        self.breaker = {m: dict(state='closed') for m in MODELS}
        self.stop_reason = None; self.last_record = time.time()
        self.totals = {}; self.notes = []; self._saved_recorded = {}
        if self.path and self.path.exists(): self._load()

    def _load(self):
        d = json.loads(self.path.read_text())
        self.notes = d.get('notes') or []; self.totals = d.get('totals') or {}
        for m, s in (d.get('models') or {}).items():
            if m not in self.breaker: continue
            if s.get('state', 'closed') != 'closed':
                self.breaker[m] = {k: s[k] for k in ('state', 'kind', 'reason', 'at') if k in s}
            self.unrecorded[m] = float(s.get('unrecorded_usd') or 0.0)
            self._saved_recorded[m] = float(s.get('recorded_usd') or 0.0)
            # A previous process died (crash, SIGKILL) with requests in flight; they may still be billed.
            lost = float(s.get('inflight_usd') or 0.0)
            if lost > 0:
                self.unrecorded[m] += lost
                self.log(f"UNRECORDED {m} +${lost:.3f} (in-flight reserve of a previous process that died without accounting)")

    # spend
    def spent(self, m):
        return self.recorded[m] + self.unrecorded[m]

    def total_spent(self):
        return sum(self.spent(m) for m in MODELS) + UNRECORDED_USD

    def allowed(self, m):
        return self.stop_reason is None and self.breaker[m]['state'] == 'closed'

    def stop(self, reason):
        with self.lock:
            if self.stop_reason is None: self.stop_reason = reason

    def acquire(self, m, sleep=time.sleep):
        """Reserve this request's estimated cost and return it, or None if the request must not be issued."""
        while True:
            with self.lock:
                if not self.allowed(m): return None
                est = self.est[m]; spent = self.total_spent(); infl = sum(self.inflight.values())
                if spent + infl + est > STOP_AT_USD:
                    self.stop_reason = 'budget'
                    msg = (f"BUDGET STOP reached: spent=${spent:.2f} inflight=${infl:.2f} next {m} est=${est:.3f} "
                           f"> stop-at ${STOP_AT_USD:.0f}")
                elif self.spent(m) + self.inflight[m] + est > MODEL_CAP_USD[m]:
                    self.breaker[m] = dict(state='capped', kind='budget', reason=f"model cap ${MODEL_CAP_USD[m]:.0f}", at=now())
                    msg = (f"MODEL CAP {m}: spent=${self.spent(m):.2f} inflight=${self.inflight[m]:.2f} est=${est:.3f} "
                           f"> cap ${MODEL_CAP_USD[m]:.0f}; no more {m} requests")
                elif spent + sum(self.inflight_worst.values()) + worst_case(m, est) <= CAP_USD:
                    self.inflight[m] += est; self.inflight_worst[m] += worst_case(m, est); self.n_inflight[m] += 1
                    msg = ''
                else:
                    msg = None
            if msg == '':
                self.save(); return est
            if msg:
                self.log(msg); self.save(); return None
            sleep(2)  # worst case of in-flight requests could pass CAP_USD; wait for some to finish

    def _unreserve(self, m, est):
        self.n_inflight[m] -= 1
        if self.n_inflight[m] <= 0:
            self.n_inflight[m] = 0; self.inflight[m] = 0.0; self.inflight_worst[m] = 0.0
        else:
            self.inflight[m] = max(self.inflight[m] - est, 0.0)
            self.inflight_worst[m] = max(self.inflight_worst[m] - worst_case(m, est), 0.0)

    def release(self, m, est):
        with self.lock: self._unreserve(m, est)

    def complete(self, m, est, rec):
        """Release the reserve and account the written record atomically; returns a BREAKER message if it tripped."""
        with self.lock:
            self._unreserve(m, est)
            return self.observe(m, rec)

    def charge_unrecorded(self, m, usd, why):
        with self.lock: self.unrecorded[m] += usd
        self.log(f"UNRECORDED {m} +${usd:.3f} ({why})")

    def abandon_inflight(self):
        """Charge reserves of requests that will never be recorded (process exit) as unrecorded spend."""
        with self.lock:
            lost = sum(self.inflight.values())
            for m in MODELS:
                self.unrecorded[m] += self.inflight[m]
                self.inflight[m] = self.inflight_worst[m] = 0.0; self.n_inflight[m] = 0
            return lost

    # breakers
    def observe(self, m, rec, live=True):
        with self.lock:
            cost = rec.get('cost') or 0.0; kind = outcome(rec)
            self.recorded[m] += cost; self.counts[m][kind] += 1
            if kind != 'error':
                self.costs[m].append(cost)
                if len(self.costs[m]) % 10 == 0: self.est[m] = max(DEFAULT_EST_USD[m], p95(self.costs[m]))
            self.window[m].append((kind, (rec.get('error') or '')[:80]))
            if live: self.last_record = time.time()
            return self._evaluate(m)

    def _evaluate(self, m):
        if self.breaker[m]['state'] != 'closed': return None
        w = list(self.window[m]); kinds = [k for k, _ in w]

        def streak(kind, n): return len(kinds) >= n and all(k == kind for k in kinds[-n:])
        trip = None
        if streak('refusal', REFUSAL_STREAK):
            trip = ('refusal', f"{REFUSAL_STREAK} consecutive refusals")
        elif kinds.count('refusal') >= REFUSALS_IN_WINDOW:
            trip = ('refusal', f"{kinds.count('refusal')} refusals in last {len(w)} calls")
        elif streak('error', SAME_ERROR_STREAK) and len({e for _, e in w[-SAME_ERROR_STREAK:]}) == 1:
            trip = ('error', f"same error {SAME_ERROR_STREAK}x in a row: {w[-1][1]}")
        elif streak('error', FAIL_STREAK):
            trip = ('error', f"{FAIL_STREAK} consecutive failed requests")
        elif kinds.count('error') >= FAILS_IN_WINDOW:
            trip = ('error', f"{kinds.count('error')} failures in last {len(w)} calls")
        if not trip: return None
        self.breaker[m] = dict(state='open', kind=trip[0], reason=trip[1], at=now())
        return f"BREAKER {trip[0]} {m} ({trip[1]})"

    def replay(self, recs):
        """Rebuild spend, estimates and breaker windows from existing records in completion order."""
        for r in recs:
            if r.get('model') not in self.breaker: continue
            msg = self.observe(r['model'], r, live=False)
            if msg: self.log(msg + ' on replay of existing records')
        with self.lock:
            for m in MODELS:
                self.recorded[m] = max(self.recorded[m], self._saved_recorded.get(m, 0.0))
                self.est[m] = max(DEFAULT_EST_USD[m], p95(self.costs[m]))

    # persistence
    def snapshot(self):
        with self.lock:
            models = {m: dict(self.breaker[m], cap_usd=MODEL_CAP_USD[m], spend_usd=round(self.spent(m), 6),
                              recorded_usd=round(self.recorded[m], 6), unrecorded_usd=round(self.unrecorded[m], 6),
                              est_per_call_usd=round(self.est[m], 6), inflight=self.n_inflight[m],
                              inflight_usd=round(self.inflight[m], 6), calls=sum(self.counts[m].values()),
                              refusal_calls=self.counts[m]['refusal'], error_calls=self.counts[m]['error'])
                      for m in MODELS}
            return dict(updated=now(), stop_at_usd=STOP_AT_USD, cap_usd=CAP_USD, unrecorded_base_usd=UNRECORDED_USD,
                        spent_usd=round(self.total_spent(), 6), inflight_usd=round(sum(self.inflight.values()), 6),
                        stop_reason=self.stop_reason, models=models, totals=self.totals, notes=self.notes)

    def save(self):
        if not self.path: return
        with self.save_lock:
            tmp = self.path.with_name(self.path.name + '.tmp')
            tmp.write_text(json.dumps(self.snapshot(), indent=1)); os.replace(tmp, self.path)


# ---------- fork probe ----------
def probe_once(model, idx, pair, hooks=None):
    hooks = hooks or {}
    if model == 'gpt-6.1-sol':
        body = {"model": model, "instructions": SYS_TOOL, "input": to_resp(pair['prompt']), "tools": [RESP_TOOL],
                "reasoning": {"effort": "high"}, "max_output_tokens": MAX_OUT[model], "prompt_cache_key": f"forkdpo-fork-{idx}"}
        d, err = call_with_retry(lambda: post(RESP_URL, body), f"{model}:{idx}", **hooks)
        if err: return dict(error=err)
        fc = [o for o in d.get('output', []) if o.get('type') == 'function_call']
        text = " ".join(c.get('text', '') for o in d.get('output', []) if o.get('type') == 'message' for c in o.get('content', []))
        cmd = None
        if fc:
            try: cmd = json.loads(fc[0].get('arguments') or '{}').get('command')
            except Exception: cmd = fc[0].get('arguments')
        return dict(finish=d.get('status'), command=cmd, text=text[:2000], usage=usage_of(model, d))
    tok_key = 'max_tokens' if model == 'glm-5.3' else 'max_completion_tokens'
    body = {"model": model, "messages": to_chat(pair['prompt'], model), "tools": CHAT_TOOLS, "tool_choice": "auto",
            "reasoning_effort": "high", tok_key: MAX_OUT[model], "stream": False}
    if model == 'claude-opus-5-5': body["cache_control"] = {"type": "ephemeral"}
    d, err = call_with_retry(lambda: post(CHAT_URL, body), f"{model}:{idx}", **hooks)
    if err: return dict(error=err)
    ch = (d.get('choices') or [{}])[0]; msg = ch.get('message') or {}
    cmd = None
    if msg.get('tool_calls'):
        try: cmd = json.loads(msg['tool_calls'][0]['function'].get('arguments') or '{}').get('command')
        except Exception: cmd = msg['tool_calls'][0]['function'].get('arguments')
    return dict(finish=ch.get('finish_reason'), command=cmd, text=(msg.get('content') or '')[:2000], usage=usage_of(model, d))


# ---------- records & summaries (shared with status.py) ----------
def read_records(path):
    out = []
    if Path(path).exists():
        for l in open(path):
            try: out.append(json.loads(l))
            except Exception: continue
    return out


def job_totals(n_pairs):
    return {m: {'probe': n_pairs * SAMPLES} for m in MODELS}


def model_summary(probe_recs, saved=None, totals=None):
    """Per-model counts, spend and projected spend; the latest record of each request decides its outcome."""
    saved = saved or {}; ms = saved.get('models') or {}; totals = totals or saved.get('totals') or {}
    out = {m: dict(done=0, ok=0, refusals=0, errors=0, recorded=0.0,
                   jobs={j: dict(spend=0.0, done=0, total=n) for j, n in (totals.get(m) or {}).items()}) for m in MODELS}
    latest = {}
    job = 'probe'
    for r in probe_recs:
        m = r.get('model')
        if m not in out: continue
        j = out[m]['jobs'].setdefault(job, dict(spend=0.0, done=0, total=0))
        j['spend'] += r.get('cost') or 0.0; out[m]['recorded'] += r.get('cost') or 0.0
        latest[(job, m, r['pair_idx'], r['sample'])] = r
    for (job, m, *_), r in latest.items():
        s = out[m]
        s[{'ok': 'ok', 'refusal': 'refusals', 'error': 'errors'}[outcome(r)]] += 1
        if finished(r): s['done'] += 1; s['jobs'][job]['done'] += 1
    for m, s in out.items():
        b = ms.get(m) or {}
        s['total'] = sum(j['total'] for j in s['jobs'].values())
        s['unrecorded'] = float(b.get('unrecorded_usd') or 0.0); s['spend'] = s['recorded'] + s['unrecorded']
        s['state'] = b.get('state', 'closed'); s['breaker'] = breaker_label(b); s['cap'] = MODEL_CAP_USD[m]
        if s['state'] != 'closed':
            s['projected'] = s['spend']
        else:
            s['projected'] = s['unrecorded'] + sum(
                j['spend'] / j['done'] * j['total'] if j['done'] else j['spend'] + DEFAULT_EST_USD[m] * j['total']
                for j in s['jobs'].values())
    return out


def summary_line(m, s):
    return (f"{m:<16} done={s['done']}/{s['total']} ok={s['ok']} refusals={s['refusals']} errors={s['errors']} "
            f"spend=${s['spend']:.2f}/${s['cap']:.0f} breaker={s['breaker']}")


def build_queue(n_pairs, done_probe, tripped):
    """One work item per (model, fork) with its unfinished samples. Items of tripped models are skipped.
    Returns (queue, n_requests, n_skipped_requests)."""
    queue = []; skipped = 0
    for idx in range(n_pairs):
        for m in MODELS:
            todo = [s for s in range(SAMPLES) if not finished(done_probe.get((m, idx, s)))]
            if not todo: continue
            if tripped(m): skipped += len(todo); continue
            queue.append(('probe', m, idx, todo))
    return queue, sum(len(it[3]) for it in queue), skipped


def write_status(head):
    summ = model_summary(read_records(RES / 'fork_probe.jsonl'), GUARD.snapshot())
    lines = [f"{head} spent=${GUARD.total_spent():.2f} done={state['done']} errors={state['err']}"]
    lines += ['  ' + summary_line(m, summ[m]) for m in MODELS]
    (ROOT / 'STATUS').write_text('\n'.join(lines) + '\n')


def exit_now(label, reason, code, status=None):
    """Stop issuing requests, charge in-flight reserves as unrecorded, persist, optionally write STATUS, and exit."""
    GUARD.stop(reason)
    lost = GUARD.abandon_inflight()
    GUARD.save()
    if status: write_status(status)
    log(f"END {label}: abandoned in-flight reserve ${lost:.2f} charged as unrecorded; spent=${GUARD.total_spent():.2f}"
        + ('' if status else '; exiting without STATUS'))
    os._exit(code)


def _on_signal(signum, frame):
    TERM.append(signum)


# ---------- driver ----------
def main():
    global GUARD
    if not os.environ.get('FORKDPO_API_KEY'):
        log('FATAL FORKDPO_API_KEY is not set'); sys.exit(2)
    signal.signal(signal.SIGTERM, _on_signal); signal.signal(signal.SIGINT, _on_signal)
    pairs = [json.loads(l) for l in open(PAIRS)]
    probe_path = RES / 'fork_probe.jsonl'
    probe_recs = read_records(probe_path)
    done_probe = {(r['model'], r['pair_idx'], r['sample']): r for r in probe_recs}
    GUARD = Guard(BREAKERS, log)
    GUARD.totals = job_totals(len(pairs))
    GUARD.replay(sorted(probe_recs, key=lambda r: r.get('ts', '')))
    GUARD.save()
    log(f"START resume: probe_done={len(done_probe)} spent=${GUARD.total_spent():.2f}")
    log("GUARD " + "; ".join(f"{m} est=${GUARD.est[m]:.3f} spend=${GUARD.spent(m):.2f}/${MODEL_CAP_USD[m]:.0f} "
                             f"{breaker_label(GUARD.breaker[m])}" for m in MODELS))

    queue, total_requests, skipped = build_queue(len(pairs), done_probe, lambda m: GUARD.breaker[m]['state'] != 'closed')
    log(f"queued {len(queue)} work items / {total_requests} requests"
        + (f"; skipped {skipped} requests of tripped models" if skipped else ''))

    out_lock = threading.Lock()

    def record(path, rec, model, kind, label, est):
        rec['cost'] = round(cost_of(model, rec['usage']), 6) if rec.get('usage') else 0.0
        rec['ts'] = now()
        with out_lock:
            with open(path, 'a') as fo: fo.write(json.dumps(rec, ensure_ascii=False) + '\n')
        trip = GUARD.complete(model, est, rec)
        GUARD.save()
        with lock:
            state['done'] += 1
            if rec.get('error'): state['err'] += 1
            n, e = state['done'], state['err']
        if rec.get('error'): log(f"ERROR {kind} {model} {label}: {rec['error'][:200]}")
        elif outcome(rec) == 'refusal': log(f"REFUSAL {kind} {model} {label}: finish={rec.get('finish')}")
        if trip: log(trip)
        if n % 100 == 0:
            log(f"PROGRESS done={n}/{total_requests} errors={e} spent=${GUARD.total_spent():.2f} "
                f"inflight=${sum(GUARD.inflight.values()):.2f} | "
                + " ".join(f"{m}=${GUARD.spent(m):.2f}" for m in MODELS))

    def issue(model, call):
        """Run one request under the rate limit and the guard; returns (result, reserve, latency), or
        (None, None, None) if it was not issued. Latency excludes the wait for the first rate-limit slot."""
        RATE.wait(model)
        est = GUARD.acquire(model)
        if est is None: return None, None, None
        hooks = dict(gate=lambda: GUARD.allowed(model), throttle=lambda: RATE.wait(model),
                     on_billed_failure=lambda: GUARD.charge_unrecorded(model, est, 'failure after request was sent'))
        t0 = time.time()
        try:
            res = call(hooks)
        except BaseException:
            GUARD.release(model, est); raise
        if res.get('error') == ABORTED:
            GUARD.release(model, est); return None, None, None
        return res, est, round(time.time() - t0, 1)

    def work(item):
        kind, model, a, samples = item
        try:
            for s in samples:
                prev = done_probe.get((model, a, s))
                res, est, lat = issue(model, lambda h: probe_once(model, a, pairs[a], h))
                if res is None: return
                rec = dict(model=model, pair_idx=a, sample=s, task_id=pairs[a].get('task_id'), kind=pairs[a].get('kind'),
                           arm=pairs[a].get('arm'), attempts=(prev.get('attempts', 1) + 1) if prev else 1, **res)
                rec['latency'] = lat
                record(probe_path, rec, model, kind, f"{a} s={s}", est)
        except Exception as e:  # never let one item kill a worker thread
            log(f"EXCEPTION {kind} {model} {a}: {type(e).__name__}: {str(e)[:200]}")

    pools = {m: cf.ThreadPoolExecutor(CONCURRENCY[m]) for m in MODELS}
    pending = {pools[item[1]].submit(work, item) for item in queue}
    while pending:
        _, pending = cf.wait(pending, timeout=5)
        if TERM:
            exit_now(f"SIGNAL {TERM[0]}", 'signal', 128 + TERM[0])
        if pending and time.time() - GUARD.last_record > STALL_SEC:
            exit_now('STALLED', 'stalled', 0, status=f"STALLED no record written for {STALL_SEC / 60:g} min with work remaining;")
    for p in pools.values(): p.shutdown()
    status = 'BUDGET_STOP' if GUARD.stop_reason == 'budget' else 'COMPLETE'
    GUARD.save()
    log(f"END {status}: done={state['done']} errors={state['err']} spent=${GUARD.total_spent():.2f}")
    write_status(status)


if __name__ == '__main__':
    main()
