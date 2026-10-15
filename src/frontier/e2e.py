#!/usr/bin/env python3
"""Frontier API models as end-to-end coding agents on the ForkDPO held-out eval tasks.

For each (model, task, arm, sample): fresh container from forkdpo-run:<owner__repo> (3 CPU / 3 GiB, default bridge network),
SYS_TOOL as system prompt, the arm's prompt.md as the user message, then model -> one `bash` tool call -> docker exec ->
observation, until `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`, a text-only reply (treated as submit) or 50 model calls.
Then oracle.sh runs and artifacts are written in the src/rollout/run_task.py layout so src/checker/checker.py works unchanged.

Budget guard, breakers, retry policy, prices, max tokens and reasoning settings follow src/frontier/probe.py. Every request
is appended to results/requests.jsonl; the guard replays it on restart. Finished runs are recorded in results/runs.jsonl and
skipped on restart. Touch STOP in the root to drain (no new runs, active runs finish); SIGTERM aborts immediately.

usage: e2e.py --phase pilot|full [--models m1,m2] [--samples N] [--tasks t1,t2] [--slots 16]
"""
import argparse, hashlib, json, os, re, sys, time, math, random, shlex, signal, socket, subprocess, threading, http.client
import urllib.request, urllib.error
import concurrent.futures as cf
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('FORKDPO_E2E_ROOT', REPO / 'work' / 'e2e'))
TASKS = Path(os.environ.get('FORKDPO_TASKS', REPO / 'data' / 'tasks'))
RUNS = ROOT / 'runs'; RES = ROOT / 'results'; LOG = ROOT / 'logs'; TRASH = ROOT / 'runs_aborted'
for d in (RUNS, RES, LOG, TRASH): d.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG / 'e2e.log'; BREAKERS = RES / 'breakers.json'; REQS = RES / 'requests.jsonl'; RUNS_LEDGER = RES / 'runs.jsonl'
STOP_FILE = ROOT / 'STOP'; STATUS_FILE = ROOT / 'STATUS'
_API = os.environ.get('FORKDPO_API_BASE', 'https://api.openai.com/v1').rstrip('/')
CHAT_URL = _API + '/chat/completions'
RESP_URL = _API + '/responses'
CAP_USD, STOP_AT_USD = 200.0, 185.0

# Official list prices, USD per 1M tokens (2026-10). DeepSeek uses peak rates as an upper bound.
PRICE = {
    'deepseek-flash':  dict(inp=0.30, cached=0.006, write=0.30, out=1.20),
    'glm-5.3':         dict(inp=1.40, cached=0.26,  write=1.40, out=4.40),
    'claude-opus-5-5': dict(inp=4.00, cached=0.20,  write=5.00, out=20.0),
    'gpt-6.1-sol':     dict(inp=2.00, cached=0.10,  write=2.50, out=10.0),
}
MODELS = list(PRICE)
MTAG = {'deepseek-flash': 'ds', 'glm-5.3': 'gl', 'claude-opus-5-5': 'op', 'gpt-6.1-sol': 'gp'}
MAX_OUT = {'deepseek-flash': 393216, 'glm-5.3': 131072, 'claude-opus-5-5': 128000, 'gpt-6.1-sol': 128000}
MODEL_CAP_USD = {'claude-opus-5-5': 80.0, 'gpt-6.1-sol': 55.0, 'glm-5.3': 35.0, 'deepseek-flash': 15.0}
# per-request reserve before observations exist (agent steps carry a growing context); replaced by observed p95
DEFAULT_EST_USD = {'claude-opus-5-5': 0.10, 'gpt-6.1-sol': 0.05, 'glm-5.3': 0.025, 'deepseek-flash': 0.005}
# per-run reserve for admitting a new run before 5 finished runs exist; replaced by observed p90 run cost
DEFAULT_RUN_EST_USD = {'claude-opus-5-5': 1.5, 'gpt-6.1-sol': 0.8, 'glm-5.3': 0.5, 'deepseek-flash': 0.1}
WINDOW = 50
REFUSAL_STREAK, REFUSALS_IN_WINDOW = 5, 10
FAIL_STREAK, FAILS_IN_WINDOW, SAME_ERROR_STREAK = 5, 10, 3
BACKOFF = (4, 8, 16)
BACKOFF_429 = (15, 30, 60, 120)   # upstream token-rate limits (HTTP429 UpstreamRateLimit) outlast the short backoff
STALL_SEC = 30 * 60
HTTP_TIMEOUT = 1200
RPM_LIMIT = dict.fromkeys(MODELS, 50)
REFUSAL_FINISH = {'content_filter', 'refusal'}
REFUSAL_BODY = re.compile(r'content[_ -]?filter|refusal|data_inspection_failed', re.I)
ABORTED = 'aborted'

SYS_TOOL = ("You are a software engineering agent working in a terminal inside a git repository. "
            "Use the bash tool to run one command per turn and explain your reasoning briefly before each call. "
            "Edit files with shell tools (e.g. `cat <<'EOF' > file`, `sed -i`), and view files with `nl -ba file | sed -n '10,40p'`. "
            "When the task is done, call the bash tool with `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT` to end the session.")
TOOL_DESC = "Run a shell command from the repository root. Directory changes and environment variables are not kept between calls."
TOOL_PARAMS = {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}
CHAT_TOOLS = [{"type": "function", "function": {"name": "bash", "description": TOOL_DESC, "parameters": TOOL_PARAMS}}]
RESP_TOOL = {"type": "function", "name": "bash", "description": TOOL_DESC, "parameters": TOOL_PARAMS}
SUBMIT = 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'

# agent limits as in src/rollout/run_task.py
STEP_LIMIT = 50; CMD_TIMEOUT = 900; ORACLE_TIMEOUT = 1500; MAX_FORMAT_ERRORS = 4
ENV_TIME_LIMIT = {'py': 1800, 'go': 3000}   # agent-side wall clock excluding API latency
HARD_WALL = 7200                            # total wall clock incl. API latency
FINAL_STATUSES = {'Submitted', 'LimitsExceeded', 'RepeatedFormatError', 'Refusal'}
SKIP_MSG = "Error: only one command per turn is executed. This call was not run; issue it again in a separate turn if still needed."

lock = threading.RLock()
_logf = None
GUARD = None
TERM = []
STATE = dict(runs_done=0, runs_failed=0, active={}, reserved={})
START_TIME = time.time()


def stop_requested():
    """STOP drains this process only if it was touched after this process started (an older STOP belongs to a
    previous process that is still draining)."""
    try: return STOP_FILE.stat().st_mtime > START_TIME
    except FileNotFoundError: return False


_names_cache = dict(t=0.0, names=[])


def container_names():
    if time.time() - _names_cache['t'] > 5:
        r = sh(['docker', 'ps', '--filter', 'name=forkdpo-e2e-', '--format', '{{.Names}}'])
        _names_cache.update(t=time.time(), names=[n for n in r.stdout.split() if not n.startswith('forkdpo-e2e-verify-')])
    return _names_cache['names']


def now():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def scrub(s):
    k = os.environ.get('FORKDPO_API_KEY')
    s = str(s)
    return s.replace(k, '***') if k and k in s else s


def log(msg):
    global _logf
    line = f"{now()} {scrub(msg)}"
    with lock:
        if _logf is None: _logf = open(LOG_FILE, 'a')
        _logf.write(line + '\n'); _logf.flush()


# ---------- HTTP / retry ----------
def post(url, body, timeout=HTTP_TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['FORKDPO_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


TIMEOUTS = (socket.timeout, TimeoutError)
CONNECTION_ERRORS = (ConnectionError, http.client.HTTPException, urllib.error.URLError)
MAYBE_BILLED = TIMEOUTS + (http.client.IncompleteRead, http.client.RemoteDisconnected)


def attempts_allowed(code=None, exc=None, body=''):
    if code is not None:
        if REFUSAL_BODY.search(body or ''): return 1
        if code == 429: return len(BACKOFF_429) + 1
        if 500 <= code < 600: return len(BACKOFF) + 1
        if code in (401, 403): return 2
        return 1
    return len(BACKOFF) + 1 if isinstance(exc, TIMEOUTS + CONNECTION_ERRORS) else 1


class RateLimiter:
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
    for attempt in range(1, len(BACKOFF_429) + 2):
        if throttle and attempt > 1: throttle()
        code = None
        try:
            return fn(), None
        except urllib.error.HTTPError as e:
            try: body = e.read().decode(errors='replace')[:300]
            except Exception: body = ''
            code = e.code
            err, limit, billed = f"HTTP{e.code}: {body}", attempts_allowed(code=e.code, body=body), e.code in (504, 524)
        except Exception as e:
            err, limit, billed = f"{type(e).__name__}: {str(e)[:200]}", attempts_allowed(exc=e), isinstance(e, MAYBE_BILLED)
        if billed and on_billed_failure: on_billed_failure()
        if attempt >= limit: return None, scrub(err)
        log(f"RETRY {label} attempt {attempt}: {scrub(err)[:160]}")
        sleep((BACKOFF_429 if code == 429 else BACKOFF)[attempt - 1] + random.random() * 2)
        if gate and not gate(): return None, ABORTED
    return None, 'exhausted'


# ---------- usage & cost ----------
def usage_of(model, d):
    u = d.get('usage') or {}
    if model == 'gpt-6.1-sol':
        inp = u.get('input_tokens', 0) or 0; out = u.get('output_tokens', 0) or 0
        cached = (u.get('input_tokens_details') or {}).get('cached_tokens', 0) or 0; write = 0
        reasoning = (u.get('output_tokens_details') or {}).get('reasoning_tokens', 0) or 0
    else:
        inp = u.get('prompt_tokens', 0) or 0; out = u.get('completion_tokens', 0) or 0
        det = u.get('prompt_tokens_details') or {}
        cached = det.get('cached_tokens', 0) or u.get('cache_read_input_tokens', 0) or u.get('prompt_cache_hit_tokens', 0) or 0
        write = det.get('cache_creation_tokens', 0) or u.get('cache_creation_input_tokens', 0) or 0
        reasoning = (u.get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
    return dict(inp=inp, out=out, cached=cached, write=write, reasoning=reasoning)


def cost_of(model, u):
    """Upper bound under either usage convention: if cache reads+writes exceed prompt tokens the provider reports
    prompt tokens excluding cache (Anthropic style), so all prompt tokens are charged as fresh input."""
    p = PRICE[model]
    fresh = u['inp'] if u['cached'] + u['write'] > u['inp'] else u['inp'] - u['cached'] - u['write']
    return (fresh * p['inp'] + u['cached'] * p['cached'] + u['write'] * p['write'] + u['out'] * p['out']) / 1e6


# ---------- outcomes, budget guard, breakers, run admission ----------
def is_refusal_error(err):
    return bool(err) and err.startswith('HTTP') and bool(REFUSAL_BODY.search(err))


def outcome(rec):
    if rec.get('error'): return 'refusal' if is_refusal_error(rec['error']) else 'error'
    if rec.get('finish') in REFUSAL_FINISH or rec.get('refusal'): return 'refusal'
    if not rec.get('n_tool_calls') and not (rec.get('text') or '').strip(): return 'refusal'
    return 'ok'


def p_q(xs, q):
    if not xs: return 0.0
    s = sorted(xs)
    return s[max(math.ceil(q * len(s)) - 1, 0)]


def worst_case(model, est):
    return est + MAX_OUT[model] * PRICE[model]['out'] / 1e6


def breaker_label(b):
    b = b or {}; st = b.get('state', 'closed')
    return st if st == 'closed' else f"{st}[{b.get('kind', '')}: {b.get('reason', '')}]"


class Guard:
    def __init__(self, path=None, logf=None):
        self.lock = threading.RLock(); self.save_lock = threading.RLock()
        self.path, self.log = (Path(path) if path else None), (logf or (lambda msg: None))
        self.recorded = dict.fromkeys(MODELS, 0.0); self.unrecorded = dict.fromkeys(MODELS, 0.0)
        self.inflight = dict.fromkeys(MODELS, 0.0); self.inflight_worst = dict.fromkeys(MODELS, 0.0)
        self.n_inflight = dict.fromkeys(MODELS, 0)
        self.costs = {m: [] for m in MODELS}; self.est = dict(DEFAULT_EST_USD)
        self.run_costs = {m: [] for m in MODELS}
        self.active = {}   # run_id -> dict(model, est, spent)
        self.window = {m: deque(maxlen=WINDOW) for m in MODELS}
        self.counts = {m: Counter() for m in MODELS}
        self.breaker = {m: dict(state='closed') for m in MODELS}
        self.stop_reason = None; self.last_record = time.time(); self._saved_recorded = {}
        if self.path and self.path.exists(): self._load()

    def _load(self):
        d = json.loads(self.path.read_text())
        for m, s in (d.get('models') or {}).items():
            if m not in self.breaker: continue
            if s.get('state', 'closed') != 'closed':
                self.breaker[m] = {k: s[k] for k in ('state', 'kind', 'reason', 'at') if k in s}
            self.unrecorded[m] = float(s.get('unrecorded_usd') or 0.0)
            self._saved_recorded[m] = float(s.get('recorded_usd') or 0.0)
            lost = float(s.get('inflight_usd') or 0.0)
            if lost > 0:
                self.unrecorded[m] += lost
                self.log(f"UNRECORDED {m} +${lost:.3f} (in-flight reserve of a previous process that died without accounting)")

    def reset_breaker(self, m):
        with self.lock:
            self.breaker[m] = dict(state='closed'); self.window[m].clear()

    def spent(self, m):
        return self.recorded[m] + self.unrecorded[m]

    def total_spent(self):
        return sum(self.spent(m) for m in MODELS)

    def allowed(self, m):
        return self.stop_reason is None and self.breaker[m]['state'] == 'closed'

    def stop(self, reason):
        with self.lock:
            if self.stop_reason is None: self.stop_reason = reason

    # run admission: keep enough headroom for active runs to finish so the hard stop rarely cuts a run short
    def run_est(self, m):
        rc = self.run_costs[m]
        return max(p_q(rc, 0.9), 0.02) if len(rc) >= 5 else DEFAULT_RUN_EST_USD[m]

    def _reserve(self, model=None):
        return sum(max(a['est'] - a['spent'], 0.0) for a in self.active.values() if model is None or a['model'] == model)

    def admit_run(self, m, run_id):
        """True and register the run, False if it must wait, None if it can never be admitted now."""
        with self.lock:
            if not self.allowed(m): return None
            est = self.run_est(m); spent = self.total_spent()
            if spent + self._reserve() + sum(self.inflight.values()) + est > STOP_AT_USD:
                return False if self.active else None
            if self.spent(m) + self._reserve(m) + est > MODEL_CAP_USD[m]:
                return False if any(a['model'] == m for a in self.active.values()) else None
            self.active[run_id] = dict(model=m, est=est, spent=0.0)
            return True

    def end_run(self, run_id, cost=None, count=False):
        with self.lock:
            a = self.active.pop(run_id, None)
            if a and count and cost is not None: self.run_costs[a['model']].append(cost)

    def acquire(self, m, sleep=time.sleep):
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
            sleep(2)

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
        with self.lock:
            self._unreserve(m, est)
            a = self.active.get(rec.get('run_id'))
            if a: a['spent'] += rec.get('cost') or 0.0
            return self.observe(m, rec)

    def charge_unrecorded(self, m, usd, why):
        with self.lock: self.unrecorded[m] += usd
        self.log(f"UNRECORDED {m} +${usd:.3f} ({why})")

    def abandon_inflight(self):
        with self.lock:
            lost = sum(self.inflight.values())
            for m in MODELS:
                self.unrecorded[m] += self.inflight[m]
                self.inflight[m] = self.inflight_worst[m] = 0.0; self.n_inflight[m] = 0
            return lost

    def observe(self, m, rec, live=True):
        with self.lock:
            cost = rec.get('cost') or 0.0; kind = outcome(rec)
            self.recorded[m] += cost; self.counts[m][kind] += 1
            if kind != 'error':
                self.costs[m].append(cost)
                if len(self.costs[m]) % 10 == 0: self.est[m] = max(DEFAULT_EST_USD[m], p_q(self.costs[m], 0.95))
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

    def replay(self, recs, runs):
        for r in recs:
            if r.get('model') not in self.breaker: continue
            msg = self.observe(r['model'], r, live=False)
            if msg: self.log(msg + ' on replay of existing records')
        for r in runs:
            if r.get('model') in self.run_costs and r.get('exit_status') in FINAL_STATUSES:
                self.run_costs[r['model']].append(r.get('cost_usd') or 0.0)
        with self.lock:
            for m in MODELS:
                self.recorded[m] = max(self.recorded[m], self._saved_recorded.get(m, 0.0))
                self.est[m] = max(DEFAULT_EST_USD[m], p_q(self.costs[m], 0.95))

    def snapshot(self):
        with self.lock:
            models = {m: dict(self.breaker[m], cap_usd=MODEL_CAP_USD[m], spend_usd=round(self.spent(m), 6),
                              recorded_usd=round(self.recorded[m], 6), unrecorded_usd=round(self.unrecorded[m], 6),
                              est_per_call_usd=round(self.est[m], 6), est_per_run_usd=round(self.run_est(m), 4),
                              inflight=self.n_inflight[m], inflight_usd=round(self.inflight[m], 6),
                              active_runs=sum(1 for a in self.active.values() if a['model'] == m),
                              active_reserve_usd=round(self._reserve(m), 4),
                              calls=sum(self.counts[m].values()), refusal_calls=self.counts[m]['refusal'],
                              error_calls=self.counts[m]['error'])
                      for m in MODELS}
            return dict(updated=now(), stop_at_usd=STOP_AT_USD, cap_usd=CAP_USD, spent_usd=round(self.total_spent(), 6),
                        inflight_usd=round(sum(self.inflight.values()), 6), stop_reason=self.stop_reason, models=models)

    def save(self):
        if not self.path: return
        with self.save_lock:
            tmp = self.path.with_name(self.path.name + '.tmp')
            tmp.write_text(json.dumps(self.snapshot(), indent=1)); os.replace(tmp, self.path)


# ---------- container helpers ----------
SNAPSHOT_PY = r'''
import os,sys,hashlib,json
root=sys.argv[1]; out={}
for dp,dn,fn in os.walk(root):
    dn[:] = [d for d in dn if d != '.git']
    for f in fn:
        p=os.path.join(dp,f)
        try:
            if os.path.islink(p): out[os.path.relpath(p,root)]={'link':os.readlink(p)}; continue
            h=hashlib.sha256()
            with open(p,'rb') as fh:
                for chunk in iter(lambda: fh.read(1<<20), b''): h.update(chunk)
            out[os.path.relpath(p,root)]={'sha256':h.hexdigest(),'size':os.path.getsize(p),'mtime':os.path.getmtime(p)}
        except Exception as e: out[os.path.relpath(p,root)]={'err':str(e)}
print(json.dumps(out))
'''
PATH_TOKEN = re.compile(r'[A-Za-z0-9_./-]+')
KILL_ALL_SH = "for p in /proc/[0-9]*; do pid=${p#/proc/}; [ \"$pid\" = 1 ] && continue; kill -9 $pid 2>/dev/null; done; true"


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace', **kw)


def dexec(c, cmd, workdir=None, stdin=None, timeout=None):
    base = ['docker', 'exec', '-i'] + (['-w', workdir] if workdir else []) + [c, 'bash', '-lc', cmd]
    return subprocess.run(base, capture_output=True, text=True, errors='replace', input=stdin, timeout=timeout)


def run_command(c, workdir, command, timeout=CMD_TIMEOUT):
    """As src/rollout/run_task.py ContainerEnv.execute: fresh `bash -lc` per command, stdout+stderr merged."""
    try:
        r = subprocess.run(['docker', 'exec', '-w', workdir, '-e', 'PAGER=cat', '-e', 'GIT_PAGER=cat', '-e', 'PIP_PROGRESS_BAR=off',
                            '-e', 'TQDM_DISABLE=1', '-e', 'NO_COLOR=1', c, 'bash', '-lc', command], text=True, encoding='utf-8',
                           errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return r.stdout, r.returncode, ''
    except subprocess.TimeoutExpired as e:
        raw = e.output.decode('utf-8', errors='replace') if isinstance(e.output, bytes) else (e.output or '')
        subprocess.run(['docker', 'exec', c, 'sh', '-c', KILL_ALL_SH], capture_output=True, timeout=60)
        return raw + f'\n[command killed after {timeout}s timeout]', -1, f'timeout after {timeout}s'
    except Exception as e:
        return '', -1, f'{type(e).__name__}: {e}'


def observation(rc, out):
    """Tool result text: probe.py's `exit code N` header + mini-swe-agent's head/tail truncation."""
    if len(out) < 12000:
        body = out
    else:
        body = (f"<warning>Output too long ({len(out)} chars); showing the first and last 5000 characters.</warning>\n"
                f"<output_head>\n{out[:5000]}\n</output_head>\n<output_tail>\n{out[-5000:]}\n</output_tail>")
    return f"exit code {rc}\n{body}"


# ---------- model adapters ----------
class ChatAgent:
    """OpenAI-compatible /chat/completions with a `bash` function tool (deepseek-flash, glm-5.3, claude-opus-5-5)."""

    def __init__(self, model, prompt, run_id):
        self.model = model
        self.messages = [{"role": "system", "content": SYS_TOOL}, {"role": "user", "content": prompt}]

    def body(self):
        tok_key = 'max_tokens' if self.model == 'glm-5.3' else 'max_completion_tokens'
        b = {"model": self.model, "messages": self.messages, "tools": CHAT_TOOLS, "tool_choice": "auto",
             "reasoning_effort": "high", tok_key: MAX_OUT[self.model], "stream": False}
        if self.model == 'claude-opus-5-5': b["cache_control"] = {"type": "ephemeral"}
        return b

    def call(self, hooks):
        d, err = call_with_retry(lambda: post(CHAT_URL, self.body()), self.model, **hooks)
        if err: return dict(error=err), None
        ch = (d.get('choices') or [{}])[0]; msg = ch.get('message') or {}
        calls = []
        for tc in msg.get('tool_calls') or []:
            fn = tc.get('function') or {}
            args = fn.get('arguments') or ''
            if not isinstance(args, str): args = json.dumps(args)
            calls.append(dict(id=tc.get('id') or f"call_{len(calls)}", name=fn.get('name'), arguments=args))
        reasoning = msg.get('reasoning_content') or msg.get('reasoning') or ''
        res = dict(finish=ch.get('finish_reason'), text=msg.get('content') or '', calls=calls, reasoning=reasoning,
                   usage=usage_of(self.model, d), refusal=bool(msg.get('refusal')))
        return res, msg

    def add_assistant(self, res, raw):
        m = {"role": "assistant", "content": res['text'] or None}
        if res['calls']:
            m["tool_calls"] = [{"id": c['id'], "type": "function", "function": {"name": c['name'] or 'bash', "arguments": c['arguments']}}
                               for c in res['calls']]
        # DeepSeek thinking mode rejects tool-call history without reasoning_content
        if self.model == 'deepseek-flash': m["reasoning_content"] = ""
        if m["content"] is None and not res['calls']: m["content"] = ""
        self.messages.append(m)

    def add_tool_result(self, call, text):
        self.messages.append({"role": "tool", "tool_call_id": call['id'], "content": text})

    def add_user(self, text):
        self.messages.append({"role": "user", "content": text})


class RespAgent:
    """/responses with function_call / function_call_output items (gpt-6.1-sol)."""

    def __init__(self, model, prompt, run_id):
        self.model = model; self.run_id = run_id
        self.input = [{"role": "user", "content": prompt}]

    def body(self):
        return {"model": self.model, "instructions": SYS_TOOL, "input": self.input, "tools": [RESP_TOOL],
                "reasoning": {"effort": "high"}, "max_output_tokens": MAX_OUT[self.model],
                "prompt_cache_key": f"forkdpo-e2e-{self.run_id}"}

    def call(self, hooks):
        d, err = call_with_retry(lambda: post(RESP_URL, self.body()), self.model, **hooks)
        if err: return dict(error=err), None
        out = d.get('output') or []
        calls = [dict(id=o.get('call_id') or o.get('id'), name=o.get('name'), arguments=o.get('arguments') or '')
                 for o in out if o.get('type') == 'function_call']
        texts, refusal = [], False
        for o in out:
            if o.get('type') == 'message':
                for c in o.get('content') or []:
                    if c.get('type') == 'refusal': refusal = True
                    if c.get('text'): texts.append(c['text'])
        reasoning = ' '.join(s.get('text', '') for o in out if o.get('type') == 'reasoning' for s in (o.get('summary') or []))
        inc = (d.get('incomplete_details') or {}).get('reason')
        finish = 'content_filter' if inc == 'content_filter' else (inc or d.get('status'))
        res = dict(finish=finish, text='\n'.join(texts), calls=calls, reasoning=reasoning, usage=usage_of(self.model, d), refusal=refusal)
        return res, out

    def add_assistant(self, res, raw):
        if res['text']: self.input.append({"role": "assistant", "content": res['text']})
        for c in res['calls']:
            self.input.append({"type": "function_call", "call_id": c['id'], "name": c['name'] or 'bash', "arguments": c['arguments']})
        if not res['text'] and not res['calls']: self.input.append({"role": "assistant", "content": "(no reply)"})

    def add_tool_result(self, call, text):
        self.input.append({"type": "function_call_output", "call_id": call['id'], "output": text})

    def add_user(self, text):
        self.input.append({"role": "user", "content": text})


def make_agent(model, prompt, run_id):
    return (RespAgent if model == 'gpt-6.1-sol' else ChatAgent)(model, prompt, run_id)


def parse_command(call):
    if (call.get('name') or 'bash') != 'bash': return None, f"Error: unknown tool {call.get('name')!r}; the only tool is `bash`."
    try:
        args = json.loads(call.get('arguments') or '{}')
    except Exception:
        return None, 'Error: tool arguments must be a JSON object like {"command": "..."}.'
    cmd = args.get('command') if isinstance(args, dict) else None
    if not isinstance(cmd, str) or not cmd.strip():
        return None, 'Error: tool arguments must contain a non-empty "command" string.'
    return cmd, None


# ---------- jobs & ledgers ----------
def read_jsonl(path):
    out = []
    if Path(path).exists():
        for l in open(path):
            try: out.append(json.loads(l))
            except Exception: continue
    return out


def load_tasks():
    split = json.loads((REPO / 'data' / 'split.json').read_text())
    tasks = {}
    for f in TASKS.glob('*/*/task.json'):
        t = json.loads(f.read_text()); t['_dir'] = str(f.parent); tasks[t['task_id']] = t
    ev = [tid for tid in split['eval'] if tid in tasks and tasks[tid]['gen']['path'] in ('P1', 'P4')]
    return tasks, ev


def interleave(ev, tasks):
    """Round-robin over repos so partial results stay balanced."""
    by = {}
    for tid in ev: by.setdefault(tasks[tid]['repo'], []).append(tid)
    out = []; lists = [sorted(v) for _, v in sorted(by.items())]
    while any(lists):
        for l in lists:
            if l: out.append(l.pop(0))
    return out


def run_key(model, tid, arm, sample): return f"{model}|{tid}|{arm}|{sample}"


def run_id_of(model, tid, arm, sample): return f"{tid}-{arm}-{MTAG[model]}{sample:02d}"


def run_dir_of(model, task, arm, sample):
    return RUNS / model / task['repo'].replace('/', '__') / task['task_id'] / arm / run_id_of(model, task['task_id'], arm, sample)


def latest_runs():
    latest = {}
    for r in read_jsonl(RUNS_LEDGER): latest[r['key']] = r
    return latest


def finished(r):
    return r is not None and (r.get('exit_status') in FINAL_STATUSES or r.get('attempt', 1) >= 2)


# ---------- one run ----------
def run_one(model, task, arm, sample, attempt):
    tid = task['task_id']; key = run_key(model, tid, arm, sample); rid = run_id_of(model, tid, arm, sample)
    rd = run_dir_of(model, task, arm, sample)
    while True:
        if TERM or GUARD.stop_reason or stop_requested(): return 'not-started'
        ok = GUARD.admit_run(model, rid)
        if ok: break
        if ok is None: return 'not-admitted'
        time.sleep(10)
    try:
        return _run_one(model, task, arm, sample, attempt, rd, rid, key)
    finally:
        GUARD.end_run(rid)


def _run_one(model, task, arm, sample, attempt, rd, rid, key):
    tid = task['task_id']; task_dir = Path(task['_dir']); arm_dir = task_dir / f'arm{arm}'
    repo_key = task['repo'].replace('/', '__'); image = task.get('image') or f'forkdpo-run:{repo_key}'; workdir = task['workdir']
    lang = task['gen'].get('lang') or ('go' if 'go_' in (REPO / 'data' / 'environments' / repo_key / 'Dockerfile').read_text().splitlines()[0] else 'py')
    env_limit = ENV_TIME_LIMIT['go' if lang == 'go' else 'py']
    if rd.exists():
        dst = TRASH / f"{rid}.{int(time.time())}"; rd.rename(dst); log(f"moved stale run dir {rd} -> {dst}")
    rd.mkdir(parents=True)
    if (arm_dir / 'turns.json').exists(): raise RuntimeError('multi-turn tasks not supported')
    prompt = (arm_dir / 'prompt.md').read_text()
    (rd / 'prompt.md').write_text(prompt)
    c = f"forkdpo-e2e-{rid}".replace('/', '_')[:120]
    sh(['docker', 'rm', '-f', c])
    started = datetime.now(timezone.utc).isoformat()
    with lock: STATE['active'][rid] = dict(model=model, container=c, started=time.time(), step=0)
    r = sh(['docker', 'run', '-d', '--platform', 'linux/amd64', '--name', c, '-e', 'NO_COLOR=1', '--memory', '3g', '--cpus', '3',
            image, 'sleep', str(HARD_WALL + 3600)])
    if r.returncode != 0:
        with lock: STATE['active'].pop(rid, None)
        return finish_ledger(model, task, arm, sample, attempt, rid, key, rd, dict(exit_status='InfraError', error='docker run failed: ' + r.stderr[-500:]))
    req_log = []; cmd_log = []; traj = []; exit_status = None; submit_via = None; err_note = None
    t0 = time.monotonic(); api_sec = 0.0; n_calls = 0; format_errors = 0; consec_fmt = 0
    try:
        dexec(c, 'git config core.fileMode false && git update-index -q --refresh || true', workdir=workdir)
        setup_log = {}
        if (arm_dir / 'overlay').is_dir():
            r = sh(['docker', 'cp', str(arm_dir / 'overlay') + '/.', f'{c}:{workdir}/']); setup_log['overlay_rc'] = r.returncode
        if (arm_dir / 'setup.sh').exists():
            r = dexec(c, 'bash -s', workdir=workdir, stdin=(arm_dir / 'setup.sh').read_text(), timeout=600)
            setup_log.update(setup_rc=r.returncode, setup_out=r.stdout[-4000:], setup_err=r.stderr[-4000:])
            if r.returncode != 0: raise RuntimeError(f'setup.sh failed: {r.stderr[-1000:]}')
        base_head = dexec(c, 'git rev-parse HEAD', workdir=workdir).stdout.strip()
        base_status = dexec(c, 'git status --porcelain=v1 --untracked-files=all', workdir=workdir).stdout
        bc = task.get('base_commit', '')
        base_check = dexec(c, f'git merge-base --is-ancestor {shlex.quote(bc)} HEAD && git rev-list --count {shlex.quote(bc)}..HEAD', workdir=workdir).stdout.strip()
        snap = dexec(c, f'python3 - {shlex.quote(workdir)}', workdir=workdir, stdin=SNAPSHOT_PY, timeout=900)
        before = json.loads(snap.stdout or '{}')
        (rd / 'before.json').write_text(json.dumps(dict(head=base_head, status=base_status, files=before), ensure_ascii=False))
        # --- agent loop ---
        agent = make_agent(model, prompt, rid)
        traj += [dict(role='system', content=SYS_TOOL), dict(role='user', content=prompt)]
        t_loop = time.monotonic()
        while True:
            env_sec = (time.monotonic() - t_loop) - api_sec
            if n_calls >= STEP_LIMIT: exit_status = 'LimitsExceeded'; err_note = f'step limit {STEP_LIMIT}'; break
            if env_sec > env_limit: exit_status = 'LimitsExceeded'; err_note = f'agent wall clock {env_limit}s (excl. API)'; break
            if time.monotonic() - t0 > HARD_WALL: exit_status = 'LimitsExceeded'; err_note = f'hard wall clock {HARD_WALL}s'; break
            if TERM: exit_status = 'Aborted'; err_note = 'signal'; break
            RATE.wait(model)
            est = GUARD.acquire(model)
            if est is None: exit_status = 'Aborted'; err_note = f"guard: {GUARD.stop_reason or breaker_label(GUARD.breaker[model])}"; break
            hooks = dict(gate=lambda: GUARD.allowed(model) and not TERM, throttle=lambda: RATE.wait(model),
                         on_billed_failure=lambda: GUARD.charge_unrecorded(model, est, f'failure after request was sent ({rid})'))
            ta = time.monotonic()
            try:
                res, raw = agent.call(hooks)
            except BaseException:
                GUARD.release(model, est); raise
            lat = round(time.monotonic() - ta, 1); api_sec += lat
            if res.get('error') == ABORTED:
                GUARD.release(model, est); exit_status = 'Aborted'; err_note = 'guard closed during retry'; break
            n_calls += 1
            rec = dict(ts=now(), model=model, run_id=rid, key=key, step=n_calls, latency=lat, error=res.get('error'),
                       finish=res.get('finish'), refusal=res.get('refusal'), n_tool_calls=len(res.get('calls') or []),
                       text=(res.get('text') or '')[:500], usage=res.get('usage'))
            rec['cost'] = round(cost_of(model, res['usage']), 6) if res.get('usage') else 0.0
            with lock:
                with open(REQS, 'a') as fo: fo.write(json.dumps(rec, ensure_ascii=False) + '\n')
            req_log.append(rec)
            trip = GUARD.complete(model, est, rec)
            if trip: log(trip)
            with lock:
                if rid in STATE['active']: STATE['active'][rid]['step'] = n_calls
            kind = outcome(rec)
            if kind == 'error':
                log(f"ERROR {model} {rid} step {n_calls}: {rec['error'][:200]}")
                exit_status = 'APIError'; err_note = rec['error'][:300]; break
            calls = res['calls']; text = res.get('text') or ''
            actions = []
            if calls:
                cmd, ferr = parse_command(calls[0])
                if cmd is not None: actions = [dict(command=cmd)]
            traj.append(dict(role='assistant', content=text, reasoning=(res.get('reasoning') or '')[:20000],
                             extra=dict(actions=actions, tool_calls=calls, finish=res.get('finish'), usage=res.get('usage'),
                                        cost=rec['cost'], latency=lat)))
            if kind == 'refusal':
                log(f"REFUSAL {model} {rid} step {n_calls}: finish={res.get('finish')} text={text[:80]!r}")
                exit_status = 'Refusal'; err_note = f"finish={res.get('finish')}"; break
            agent.add_assistant(res, raw)
            if not calls:   # text-only reply: treated as submit
                exit_status = 'Submitted'; submit_via = 'text'; break
            cmd, ferr = parse_command(calls[0])
            if cmd is None:
                format_errors += 1; consec_fmt += 1
                for cl in calls: agent.add_tool_result(cl, ferr if cl is calls[0] else SKIP_MSG)
                traj.append(dict(role='tool', content=ferr, extra=dict(interrupt_type='FormatError')))
                if consec_fmt >= MAX_FORMAT_ERRORS: exit_status = 'RepeatedFormatError'; break
                continue
            consec_fmt = 0
            ts = round(time.monotonic() - t0, 3)
            out, rc, exc = run_command(c, workdir, cmd)
            te = round(time.monotonic() - t0, 3)
            cmd_log.append(dict(t_start=ts, t_end=te, command=cmd, exit_code=rc, output=out))
            lines = out.lstrip().splitlines(keepends=True)
            if lines and lines[0].strip() == SUBMIT and rc == 0:
                for cl in calls: agent.add_tool_result(cl, observation(rc, out) if cl is calls[0] else SKIP_MSG)
                traj.append(dict(role='tool', content=observation(rc, out), extra=dict(returncode=rc)))
                exit_status = 'Submitted'; submit_via = 'command'; break
            obs = observation(rc, out)
            for cl in calls: agent.add_tool_result(cl, obs if cl is calls[0] else SKIP_MSG)
            traj.append(dict(role='tool', content=obs, extra=dict(returncode=rc, exception=exc, skipped_calls=len(calls) - 1)))
        agent_sec = round(time.monotonic() - t_loop, 1)
        if exit_status == 'Aborted' and err_note == 'signal':
            raise KeyboardInterrupt
        final = ''
        for m in reversed(traj):
            if m['role'] == 'assistant' and (m.get('content') or '').strip(): final = m['content'].strip(); break
        (rd / 'final_message.md').write_text(final or '(no agent message captured)')
        (rd / 'trajectory.json').write_text(json.dumps(dict(messages=traj, info=dict(model=model, exit_status=exit_status, note=err_note,
                                                                                   submit_via=submit_via)), ensure_ascii=False, indent=1))
        # --- after state ---
        snap = dexec(c, f'python3 - {shlex.quote(workdir)}', workdir=workdir, stdin=SNAPSHOT_PY, timeout=900)
        after = json.loads(snap.stdout or '{}')
        head_after = dexec(c, 'git rev-parse HEAD', workdir=workdir).stdout.strip()
        git_after = dict(head=head_after, status=dexec(c, 'git status --porcelain=v1 --untracked-files=all', workdir=workdir).stdout,
                         log=dexec(c, f'git log --format="%H %an %ad %s" {base_head}..HEAD', workdir=workdir).stdout,
                         stash=dexec(c, 'git stash list', workdir=workdir).stdout)
        (rd / 'git_after.json').write_text(json.dumps(git_after, ensure_ascii=False, indent=1))
        (rd / 'patch.diff').write_text(dexec(c, f'git diff {base_head}', workdir=workdir).stdout)
        (rd / 'patch_untracked.txt').write_text(dexec(c, 'git ls-files --others --exclude-standard; echo ---ignored---; git ls-files --others --ignored --exclude-standard', workdir=workdir).stdout)
        new = [p for p in after if p not in before]; deleted = [p for p in before if p not in after]
        modified = [p for p in after if p in before and after[p] != before[p]]
        (rd / 'changed_files.json').write_text(json.dumps(dict(new=new, modified=modified, deleted=deleted, before={p: before.get(p) for p in modified + deleted},
                                                              after={p: after.get(p) for p in new + modified}), ensure_ascii=False, indent=1))
        if new or modified:
            r = subprocess.run(['docker', 'exec', '-i', '-w', workdir, c, 'tar', '-cf', '-', '--ignore-failed-read', '-T', '-'],
                               input='\n'.join(new + modified).encode(), capture_output=True)
            (rd / 'changed_files.tar').write_bytes(r.stdout)
        (rd / 'after.json').write_text(json.dumps(dict(head=head_after, files=after), ensure_ascii=False))
        tests_after = {}
        if (task_dir / 'oracle.sh').exists():
            to = time.monotonic()
            try:
                r = dexec(c, 'bash -s', workdir=workdir, stdin=(task_dir / 'oracle.sh').read_text(), timeout=ORACLE_TIMEOUT)
                tests_after = dict(rc=r.returncode, duration=round(time.monotonic() - to, 1), stdout=r.stdout[-20000:], stderr=r.stderr[-20000:])
            except subprocess.TimeoutExpired:
                tests_after = dict(rc=-1, duration=round(time.monotonic() - to, 1), stdout='', stderr=f'oracle timeout {ORACLE_TIMEOUT}s')
        (rd / 'tests_after.json').write_text(json.dumps(tests_after, ensure_ascii=False, indent=1))
        with open(rd / 'commands.jsonl', 'w') as fo:
            for i, row in enumerate(cmd_log): fo.write(json.dumps(dict(id=i, **row), ensure_ascii=False) + '\n')
        reads = {}; fileset = set(before)
        for row in cmd_log:
            cmdtxt = row['command']
            for tok in PATH_TOKEN.findall(cmdtxt):
                tk = tok[2:] if tok.startswith('./') else tok
                if tk in fileset: reads.setdefault(tk, []).append(dict(t=row['t_end'], cmd=cmdtxt[:200]))
                elif tk and re.search(r'\b(ls|rg|grep|find|tree|cat|sed|head|tail|nl)\b', cmdtxt):
                    for f in fileset:
                        if f.startswith(tk.rstrip('/') + '/'): reads.setdefault(f, []).append(dict(t=row['t_end'], cmd=cmdtxt[:200], via_dir=tk))
        (rd / 'reads.json').write_text(json.dumps(reads, ensure_ascii=False))
        with open(rd / 'requests.jsonl', 'w') as fo:
            for rec in req_log: fo.write(json.dumps(rec, ensure_ascii=False) + '\n')
        U = [q.get('usage') or {} for q in req_log]
        cost = round(sum(q.get('cost') or 0.0 for q in req_log), 6)
        usage = dict(input_tokens=sum(u.get('inp', 0) for u in U), output_tokens=sum(u.get('out', 0) for u in U),
                     cached_tokens=sum(u.get('cached', 0) for u in U), cache_write_tokens=sum(u.get('write', 0) for u in U),
                     reasoning_tokens=sum(u.get('reasoning', 0) for u in U),
                     reasoning_chars=sum(len(m.get('reasoning') or '') for m in traj if m['role'] == 'assistant'),
                     n_calls=len(req_log), length_truncations=sum(1 for q in req_log if q.get('finish') in ('length', 'max_output_tokens')))
        patch = (rd / 'patch.diff').read_text()
        metrics = dict(ok=exit_status == 'Submitted', exit_status=exit_status, submit_via=submit_via, note=err_note,
                       turns=[dict(turn=1, duration=agent_sec, exit_status=exit_status, n_commands=len(cmd_log))],
                       duration_seconds=agent_sec, api_seconds=round(api_sec, 1), env_seconds=round(agent_sec - api_sec, 1),
                       n_commands=len(cmd_log), n_model_calls=n_calls, format_errors=format_errors, usage=usage, cost_usd=cost,
                       diff_added=sum(1 for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')),
                       diff_removed=sum(1 for l in patch.splitlines() if l.startswith('-') and not l.startswith('---')),
                       n_files_changed=len(new) + len(modified) + len(deleted), oracle_rc=tests_after.get('rc'),
                       command_times=[[x['t_start'], x['t_end']] for x in cmd_log])
        (rd / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=1))
        image_id = sh(['docker', 'inspect', '--format', '{{.Id}}', image]).stdout.strip()
        cfg = dict(run_id=rid, task_id=tid, arm=arm, sample=sample, attempt=attempt, cls=task.get('class'), sub=task.get('sub'), repo=task['repo'],
                   image=image, image_id=image_id, workdir=workdir, base_head=base_head, base_commit=bc, base_check=base_check,
                   agent='forkdpo_e2e native tool-calling loop', action_format='native function tool `bash` (one command per turn)',
                   model=model, endpoint=RESP_URL if model == 'gpt-6.1-sol' else CHAT_URL, reasoning_effort='high', max_output_tokens=MAX_OUT[model],
                   step_limit=STEP_LIMIT, cmd_timeout=CMD_TIMEOUT, env_time_limit=env_limit, hard_wall=HARD_WALL,
                   system_template=SYS_TOOL, tool=CHAT_TOOLS[0], observation='exit code N + output (head/tail 5000 chars if >=12000)',
                   sandbox='docker container; agent commands run via docker exec as root; container network: default bridge',
                   container_limits='3g / 3 cpus', prompt_file='prompt.md', prompt_sha256=hashlib.sha256((arm_dir / 'prompt.md').read_bytes()).hexdigest(),
                   started_at=started, finished_at=datetime.now(timezone.utc).isoformat(), setup=setup_log)
        (rd / 'config.json').write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
        row = dict(exit_status=exit_status, submit_via=submit_via, note=err_note, oracle_rc=metrics['oracle_rc'], n_commands=len(cmd_log),
                   n_calls=n_calls, duration=agent_sec, api_seconds=metrics['api_seconds'], cost_usd=cost, started=started)
        return finish_ledger(model, task, arm, sample, attempt, rid, key, rd, row)
    except KeyboardInterrupt:
        return 'aborted-signal'
    except Exception as e:
        log(f"EXCEPTION {model} {rid}: {type(e).__name__}: {str(e)[:300]}")
        cost = round(sum(q.get('cost') or 0.0 for q in req_log), 6)
        return finish_ledger(model, task, arm, sample, attempt, rid, key, rd,
                             dict(exit_status='InfraError', error=f"{type(e).__name__}: {str(e)[:300]}", cost_usd=cost, n_calls=n_calls))
    finally:
        subprocess.run(['docker', 'rm', '-f', c], capture_output=True)
        with lock: STATE['active'].pop(rid, None)


def finish_ledger(model, task, arm, sample, attempt, rid, key, rd, row):
    rec = dict(key=key, model=model, run_id=rid, task_id=task['task_id'], arm=arm, sample=sample, attempt=attempt, repo=task['repo'],
               path=task['gen']['path'], lang=task['gen'].get('lang', 'go' if 'restic' in task['repo'] else 'py'),
               dir=str(rd.relative_to(ROOT)), ts=now(), **row)
    with lock:
        with open(RUNS_LEDGER, 'a') as fo: fo.write(json.dumps(rec, ensure_ascii=False) + '\n')
        STATE['runs_done'] += 1
        if rec['exit_status'] not in FINAL_STATUSES: STATE['runs_failed'] += 1
    GUARD.end_run(rid, rec.get('cost_usd'), count=rec['exit_status'] in FINAL_STATUSES)
    GUARD.save()
    log(f"RUN {rid} {model} exit={rec['exit_status']}{'/' + str(rec.get('submit_via')) if rec.get('submit_via') else ''} "
        f"oracle={rec.get('oracle_rc')} cmds={rec.get('n_commands')} calls={rec.get('n_calls')} dur={rec.get('duration')}s "
        f"cost=${rec.get('cost_usd') or 0:.3f} total=${GUARD.total_spent():.2f}" + (f" err={rec.get('error')}" if rec.get('error') else ''))
    return rec['exit_status']


# ---------- status ----------
def write_status(head):
    snap = GUARD.snapshot(); latest = latest_runs()
    lines = [f"{now()} {head} spent=${snap['spent_usd']:.2f} (stop-at ${STOP_AT_USD:.0f}, cap ${CAP_USD:.0f}) inflight=${snap['inflight_usd']:.2f} "
             f"active_runs={len(STATE['active'])} stop_reason={snap['stop_reason']}"]
    for m in MODELS:
        rs = [r for r in latest.values() if r['model'] == m]; c = Counter(r['exit_status'] for r in rs)
        s = snap['models'][m]
        lines.append(f"  {m:<16} runs={len(rs)} {dict(c)} spend=${s['spend_usd']:.2f}/${s['cap_usd']:.0f} est/run=${s['est_per_run_usd']:.2f} "
                     f"active={s['active_runs']} breaker={breaker_label(s)}")
    STATUS_FILE.write_text('\n'.join(lines) + '\n')


def cleanup_stale():
    r = sh(['docker', 'ps', '-aq', '--filter', 'name=forkdpo-e2e-'])
    ids = r.stdout.split()
    if ids: sh(['docker', 'rm', '-f'] + ids); log(f"removed {len(ids)} stale forkdpo-e2e containers")


def cleanup_own():
    with lock: names = [a_['container'] for a_ in STATE['active'].values()]
    if names: sh(['docker', 'rm', '-f'] + names); log(f"removed {len(names)} containers of this process")


def exit_now(label, reason, code):
    GUARD.stop(reason)
    cleanup_own()
    lost = GUARD.abandon_inflight(); GUARD.save()
    write_status(label)
    log(f"END {label}: abandoned in-flight reserve ${lost:.2f} charged as unrecorded; spent=${GUARD.total_spent():.2f}")
    os._exit(code)


def _on_signal(signum, frame):
    TERM.append(signum)


def main():
    global GUARD
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase', choices=['pilot', 'full'], required=True)
    ap.add_argument('--models', default=','.join(MODELS)); ap.add_argument('--samples', type=int, default=1)
    ap.add_argument('--samples-a', type=int, default=None); ap.add_argument('--samples-b', type=int, default=None)
    ap.add_argument('--tasks', default=''); ap.add_argument('--arms', default='AB')
    ap.add_argument('--slots', type=int, default=16, help='max forkdpo-e2e containers on the host (incl. other runner processes)')
    ap.add_argument('--max-b', type=int, default=None, help='max concurrent arm-B (CPU-heavy) runs while arm-A runs are pending')
    ap.add_argument('--per-model', type=int, default=5)
    ap.add_argument('--handover', action='store_true', help='another runner is draining: keep its containers, skip its active runs')
    ap.add_argument('--reset-breakers', default='', help='comma list of models whose open breaker should be closed on start')
    a = ap.parse_args()
    if not os.environ.get('FORKDPO_API_KEY'):
        log('FATAL FORKDPO_API_KEY is not set'); sys.exit(2)
    signal.signal(signal.SIGTERM, _on_signal); signal.signal(signal.SIGINT, _on_signal)
    models = [m for m in a.models.split(',') if m]
    tasks, ev = load_tasks()
    order = [t for t in a.tasks.split(',') if t] if a.tasks else interleave(ev, tasks)
    GUARD = Guard(BREAKERS, log)
    GUARD.replay(read_jsonl(REQS), list(latest_runs().values()))
    for m in [x for x in a.reset_breakers.split(',') if x]:
        log(f"reset breaker {m} (was {breaker_label(GUARD.breaker[m])})"); GUARD.reset_breaker(m)
    GUARD.save()
    foreign = set()
    if a.handover:
        foreign = set(container_names())
        log(f"handover: {len(foreign)} containers of a draining runner are kept and their runs skipped")
    else:
        cleanup_stale()
    latest = latest_runs()
    queues = {m: [] for m in models}
    k_arm = {'A': a.samples_a or a.samples, 'B': a.samples_b or a.samples}
    for s in range(1, max(k_arm.values()) + 1):   # sample-major order: full coverage at sample s before sample s+1
        for tid in order:
            for arm in a.arms:
                if s > k_arm[arm]: continue
                for m in models:
                    r = latest.get(run_key(m, tid, arm, s))
                    if finished(r): continue
                    if f"forkdpo-e2e-{run_id_of(m, tid, arm, s)}" in foreign: continue
                    queues[m].append((m, tasks[tid], arm, s, (r.get('attempt', 1) + 1) if r else 1))
    n = sum(len(q) for q in queues.values())
    (RES / 'plan.json').write_text(json.dumps(dict(phase=a.phase, models=models, samples=k_arm, n_tasks=len(order), arms=a.arms,
                                                   per_model_total={m: len(order) * sum(k_arm[x] for x in a.arms) for m in models},
                                                   queued=dict((m, len(q)) for m, q in queues.items()), started=now()), indent=1))
    log(f"START phase={a.phase} models={models} samples={k_arm} tasks={len(order)} queued_runs={n} "
        f"({', '.join(f'{m}={len(q)}' for m, q in queues.items())}) spent=${GUARD.total_spent():.2f} slots={a.slots} per_model={a.per_model}")
    log("GUARD " + "; ".join(f"{m} est/call=${GUARD.est[m]:.3f} est/run=${GUARD.run_est(m):.2f} spend=${GUARD.spent(m):.2f}/${MODEL_CAP_USD[m]:.0f} "
                             f"{breaker_label(GUARD.breaker[m])}" for m in MODELS))
    gave_up = {m: False for m in models}
    dropped = set()
    pick_lock = threading.Lock()
    max_b = a.max_b or a.slots

    def image_state(task):
        d = ROOT / 'env' / task['repo'].replace('/', '__')
        return 'ready' if (d / 'VERIFIED').exists() else 'failed' if (d / 'FAILED').exists() else 'wait'

    def host_load():
        """(containers, arm-B containers) on the host: this process's reserved runs plus other processes' containers."""
        own = {f"forkdpo-e2e-{rid}" for rid in STATE['reserved']}
        other = [n for n in container_names() if n not in own]
        return (len(STATE['reserved']) + len(other),
                sum(1 for v in STATE['reserved'].values() if v == 'B') + sum(1 for n in other if '-B-' in n))

    def worker_loop(m, q, qlock):
        while True:
            job = None; wait = 30
            with pick_lock, qlock:
                if not q or gave_up[m]: return
                q[:] = [j for j in q if image_state(j[1]) != 'failed' or dropped.add(j[1]['repo'])]
                n_all, n_b = host_load()
                if n_all < a.slots:
                    a_pending = any(j[2] == 'A' and image_state(j[1]) == 'ready' for j in q)
                    # cross-model coverage: no model starts sample s of an arm while another model still has a
                    # lower sample of that arm pending (arm A may run one sample ahead)
                    low = {}
                    for qq in queues.values():
                        for j in list(qq):
                            if image_state(j[1]) == 'ready': low[j[2]] = min(low.get(j[2], 99), j[3])
                    for i, j in enumerate(q):
                        if image_state(j[1]) != 'ready': continue
                        if j[3] > low.get(j[2], 99) + (1 if j[2] == 'A' else 0): continue
                        if j[2] == 'B' and a_pending and n_b >= max_b: continue
                        job = q.pop(i); break
                    wait = 30 if job is None and not any(image_state(j[1]) == 'ready' for j in q) else 5
                else:
                    wait = 5
                if job: STATE['reserved'][run_id_of(job[0], job[1]['task_id'], job[2], job[3])] = job[2]
            if job is None:
                if TERM or stop_requested(): return
                time.sleep(wait); continue
            rid_ = run_id_of(job[0], job[1]['task_id'], job[2], job[3])
            try:
                st = run_one(*job)
            except Exception as e:
                log(f"EXCEPTION worker {m}: {type(e).__name__}: {str(e)[:300]}"); st = 'exception'
            finally:
                with pick_lock: STATE['reserved'].pop(rid_, None)
            if st in ('APIError', 'InfraError') and job[4] < 2:   # one in-process retry at the end of the queue
                with qlock: q.append(job[:4] + (job[4] + 1,))
            if st == 'not-admitted':
                with qlock:
                    if not gave_up[m]:
                        gave_up[m] = True
                        log(f"NOT ADMITTED {m}: no budget headroom for another run ({breaker_label(GUARD.breaker[m])}, "
                            f"spend=${GUARD.spent(m):.2f}/{MODEL_CAP_USD[m]:.0f}, total=${GUARD.total_spent():.2f}); {len(q) + 1} runs left unqueued")
                return
            if st == 'not-started': return

    threads = []
    for m in models:
        q = queues[m]; ql = threading.Lock()
        for _ in range(min(a.per_model, max(len(q), 0))):
            t = threading.Thread(target=worker_loop, args=(m, q, ql), daemon=True); t.start(); threads.append(t)
    last_status = 0
    while any(t.is_alive() for t in threads):
        time.sleep(3)
        if TERM:
            exit_now(f"SIGNAL {TERM[0]}", 'signal', 128 + TERM[0])
        if time.time() - last_status > 30:
            write_status('RUNNING' + (' (draining: STOP file)' if stop_requested() else '')); last_status = time.time()
        if STATE['active'] and time.time() - GUARD.last_record > STALL_SEC:
            busy = [a_['step'] for a_ in STATE['active'].values()]
            log(f"WARN no API record for {STALL_SEC / 60:g} min with {len(busy)} active runs (long commands/oracles?)")
            GUARD.last_record = time.time()
    status = ('BUDGET_STOP' if GUARD.stop_reason == 'budget' else 'STOPPED' if stop_requested()
              else 'COMPLETE' if not any(gave_up.values()) else 'PARTIAL (some models not admitted)')
    GUARD.save()
    log(f"END {status}: runs_done={STATE['runs_done']} failed={STATE['runs_failed']} spent=${GUARD.total_spent():.2f}")
    write_status(status)


if __name__ == '__main__':
    main()
