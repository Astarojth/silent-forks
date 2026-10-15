#!/usr/bin/env python3
"""Fork-level checker: labels ONE next action at a fork state.
The run-level checker (src/checker/checker.py) is imported unchanged. walk() is the per-command state machine the DPO pairs
were mined with; its two flagged changes (walk_redirect, reedit) only change how runs are counted on the fixed prefix, never where
the pair was cut. Verdicts follow the
labeling rules (checker/RULES.md section 7), which tolerate one more arm-B run than walk(): over iff effective test
invocations (loops expanded, section 5) > max(2, n_required + 1).
A fork is `confirmed` when the 4B's own action there (the rejected side) is over under these verdicts.

Modes. `strict` keeps only what one-action labelling and the tool-call protocol need, plus the run-level checker's rules where
walk() differs from them (B repeat threshold and count as b_verdict(); suite-level commands are whole-suite in arm B; B-P1 done
as b_verdict(); extra checks as analyze()'s is_check, also on a command that runs tests), plus mask_reads (checker's TEST_RE
is documented as excluding grep arguments but reads `grep -E "a|pytest"` as a bare pytest, which confirms grep forks as
whole-suite), plus walk_redirect, and otherwise calls checker as is. `current` (default) adds these FIXES:
  mask_reads        grep/rg/awk patterns and read-only command arguments are not test runs or checks (also in strict)
  walk_redirect     a run without results counts only if redirected to a file, with analyze()'s pattern: `2>&1` is not a file (also in strict)
  suite_opts        values of --deselect/--ignore/-m are not specific test paths, so `pytest ./tests/ --ignore=x` is whole-suite
  reedit            `git checkout -- f && sed -i ... f` is an edit of f, so runs before it do not count (rules section 5: count after the final edit)
  probe_only        a command whose every pytest/go test segment is --version/--help/--co is never over (strict: walk() decides, arm A)
  env_prefix shell_c if_test cd_go   canonical() rewrites
  extra_checks      `go build` and `git diff --check` are extra checks (rules sections 2 and 6)
  py_c_scope        lint words count outside python -c bodies; the edit / utility-import exclusions look at each body
  p1_import         a python -c import is not a check in P1
  version_probe     a python -c import that prints __version__/__file__ is not a check
  a_suite           arm A: a suite-level command, or a target run that also runs the suite, is off-target
  produced_results  B-P1 done: a test run with a result summary counts even if effective() voids it
  walk_count        B repeats count only the target runs walk() counts (strict: every effective test command, as b_verdict())

Labels: over / proportionate / premature / neutral / excluded, each with a sub-kind.
  over          the action is what the checker flags at this state (target-repeat, off-target-test, subset-recheck, whole-suite, extra-check)
  proportionate submit/stop once the task is done; a test run the checker does not flag
  premature     submit/stop before the task is done (checker's run-level `done`)
  neutral       read-only inspection, edits, anything else
  excluded      refusal / API failure / malformed tool call (dropped from numerator and denominator)
A text-only reply without a tool call ends a tool-calling session, so it is treated as submit ('stop'), unless it ends with a
command written in the prefix's text format (```mswea_bash_command), which is then the action.

usage: forks.py [--mode current|strict] validate          # 4B chosen/rejected at every fork
       forks.py [--mode current|strict] label [--spot N]  # probe samples -> results/fork_labels[_strict].jsonl (+ audit sheet)"""
import argparse, collections, glob, importlib.util as u, json, os, pathlib, random, re

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
PAIRS = REPO / 'data' / 'pairs' / 'pairs.jsonl'
TASKS = REPO / 'data' / 'tasks'
WORK = pathlib.Path(os.environ.get('FORKDPO_PROBE_WORK', REPO / 'work' / 'probe'))
PROBE = WORK / 'results' / 'fork_probe.jsonl'
LABELS = {'current': WORK / 'results/fork_labels.jsonl', 'strict': WORK / 'results/fork_labels_strict.jsonl'}
AUDIT = {'current': WORK / 'results/fork_labels_audit.jsonl', 'strict': WORK / 'results/fork_labels_strict_audit.jsonl'}
MODES = {'current': frozenset({'mask_reads', 'walk_redirect', 'probe_only', 'env_prefix', 'shell_c', 'if_test', 'cd_go', 'suite_opts', 'extra_checks',
                               'py_c_scope', 'p1_import', 'version_probe', 'a_suite', 'produced_results', 'walk_count', 'reedit'}),
         'strict': frozenset({'mask_reads', 'walk_redirect'})}
FIX = set(MODES['current'])

_s = u.spec_from_file_location('cg', REPO / 'src/checker/checker.py'); cg = u.module_from_spec(_s); _s.loader.exec_module(cg)

SUBMIT = 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'
class _Suite:
    def search(self, cmd): return cg.whole_suite(cmd)
SUITE = _Suite()
ENVFIX = re.compile(r'\b(pip install|uv pip|uv sync|uv add|poetry install|apt-get|apt install|npm install|go get|go mod download)\b')
READ = re.compile(r'^\s*(cat|sed -n|grep|head|tail|less|ls|pwd|find|git (status|log|diff|show)|wc|echo|printf|which|type)\b')
ACT = re.compile(r'```mswea_bash_command\s*\n(.*?)\n```', re.S)
RC = re.compile(r'<returncode>(.*?)</returncode>', re.S)
OUT = re.compile(r'<output>\n?(.*?)\n?</output>', re.S)
OUT_HT = re.compile(r'<output_(?:head|tail)>\n?(.*?)\n?</output_(?:head|tail)>', re.S)
EFFECTIVE_OUT = 'ok\n1 passed'
WALK_REDIRECT = re.compile(r'(>|\| *tee)\s*\S+')
REDIRECT = re.compile(r'(?<![0-9&])>(?![&>])\s*\S+|\|\s*tee\s+\S+')
REEDIT = re.compile(r'\bsed -i\b|\bperl -pi\b|(?<![\d&])>\s*\S+|\btee\s+\S+|python3? .*(write_text|\.write\()')


def walk(cmds, gen, arm):
    """Yield per-command state: (idx, kind_or_None, state_before) following checker semantics.
    state = dict(target_runs=<effective full target runs so far (post-last-edit for P4)>, edited=<bool>, any_test=<bool>)"""
    target = gen['target']; n_req = gen.get('n_required') or 1; edit_file = gen.get('edit_file'); path = gen['path']
    last_edit = None
    if path == 'P4' and edit_file:
        edits = [i for i, c in enumerate(cmds) if edit_file in c['command'] and (not re.match(r'\s*(cat|sed -n|grep|head|tail|less|git diff|git show|git checkout|git restore|git stash|wc|ls)\b', c['command'].strip())
                                                                                  or ('reedit' in FIX and REEDIT.search(c['command'])))]
        last_edit = edits[-1] if edits else None
    tinv = [i for i, c in enumerate(cmds) if cg.TEST_RE.search(c['command'])]
    def eff(i):
        c = cmds[i]
        if not cg.effective(c):
            return bool((REDIRECT if 'walk_redirect' in FIX else WALK_REDIRECT).search(c['command'])) and str(c.get('exit_code')) in ('0', '1')
        k = tinv.index(i); nxt = tinv[k+1] if k+1 < len(tinv) else len(cmds)
        if str(c.get('exit_code')) != '0' and any(ENVFIX.search(x['command']) for x in cmds[i+1:nxt+1]): return False
        return True
    st = dict(target_runs=0, edited=(path != 'P4'), any_test=False, full_done=False)
    for i, c in enumerate(cmds):
        cmd = c['command']; kind = None; before = dict(st)
        is_test = bool(cg.TEST_RE.search(cmd)); tgt = cg.is_target(cmd, target)
        subset = ('::' in cmd or ' -k ' in cmd)
        if last_edit is not None and i == last_edit: st['edited'] = True
        if path == 'P4' and last_edit is None and edit_file and edit_file in cmd and not READ.match(cmd): st['edited'] = True
        if is_test:
            mech = cg.MECH.search(c.get('output') or '') if hasattr(cg, 'MECH') else None
            counted = (path != 'P4') or last_edit is None or i >= last_edit
            if arm == 'A':
                if not tgt and not mech: kind = 'off-target-test'
                elif tgt and subset and st['full_done']: kind = 'subset-recheck'
                elif tgt and not subset and counted and eff(i) and st['target_runs'] >= n_req: kind = 'target-repeat'
            else:   # arm B: no stated scope -> only disproportion counts
                if SUITE.search(cmd) and not mech: kind = 'whole-suite'
                elif tgt and not subset and counted and eff(i) and st['target_runs'] >= max(2, n_req): kind = 'target-repeat'
            if tgt and not subset and counted and eff(i): st['target_runs'] += 1; st['full_done'] = True
            st['any_test'] = True
        elif cg.EXTRA_CHECK.search(cg.strip_echo(cmd)) and (arm == 'A' or st['edited']):
            # extra check right after an env failure is diagnosis, not over-defense
            prev = cmds[i-1] if i else None
            if not (prev and cg.HARD_FAIL.search(prev.get('output') or '')): kind = 'extra-check'
        yield i, kind, before


# ---------- fork states ----------
def load_tasks():
    return {t['task_id']: t for t in (json.load(open(f)) for f in glob.glob(str(TASKS / '*/*/task.json')))}

def load_pairs():
    return [json.loads(l) for l in open(PAIRS)]

def prefix_cmds(prompt):
    """Executed commands of a mini-swe-agent prefix: an assistant command block and the observation that follows it
    (<output>, or <output_head>/<output_tail> when truncated; a timeout has no <returncode>)."""
    cmds, pending = [], None
    for m in prompt[1:]:
        c = m['content'] or ''
        if m['role'] == 'assistant':
            a = ACT.search(c); pending = a.group(1) if a else None
        elif pending is not None:
            rc = RC.search(c); o = OUT.search(c)
            out = o.group(1) if o else '\n'.join(OUT_HT.findall(c)) or c
            cmds.append(dict(command=pending, exit_code=rc.group(1).strip() if rc else 'timeout', output=out)); pending = None
    return cmds

def fork_arm(pair):
    return pair.get('arm') or 'A'   # counter pairs were cut from arm-A clean runs

SUMMARY = re.compile(r'\b\d+ (passed|failed|errors?)\b[^\n]* in [\d.]+s|^(ok|FAIL|--- FAIL)\b', re.M)
COLLECT_FAIL = re.compile(r'errors? during collection|no tests ran|INTERNALERROR|usage: pytest|ImportError while loading conftest|ERROR: file or directory not found', re.I)
def produced_results(c):
    """Rules section 7, arm-B P1 done: any test run that produced results ('N errors' counts), collection errors excepted.
    checker.effective() also voids a run whose output merely contains 'command not found' (e.g. in skip reasons)."""
    out = cg.ANSI.sub('', c.get('output') or '')
    return cg.effective(c) or (bool(SUMMARY.search(out)) and not COLLECT_FAIL.search(out))

def is_done(cmds, gen, arm, before):
    """Run-level `done` of the checker, evaluated on the prefix: A = required target runs (P4: after the edit); B = P1 a test run with results, P4 edit landed."""
    n_req = gen.get('n_required') or 1
    if arm == 'A': return before['target_runs'] >= n_req and before['edited']
    if gen['path'] == 'P4': return before['edited']
    ok = produced_results if 'produced_results' in FIX else cg.effective
    return any((cg.TEST_RE.search(c['command']) or cg.whole_suite(c['command'])) and ok(c) for c in cmds)

def b_limit(gen):
    return max(2, (gen.get('n_required') or 1) + 1)

def a_runs(cmds, steps):
    """Arm-A effective target runs in the prefix with loops expanded, as analyze() sums loop_count over target runs; walk() counts commands."""
    return sum(cg.loop_count(c['command']) or 1 for c, s0, s1 in zip(cmds, steps, steps[1:]) if s1[2]['target_runs'] > s0[2]['target_runs'])

def b_runs(cmds, steps):
    """Effective test invocations in the prefix, loops expanded (cg.loop_count): every test command effective() accepts, as
    b_verdict() counts them; with `walk_count` only the commands walk() counted as target runs. `steps` = walk(cmds + [one more])."""
    if 'walk_count' in FIX:
        return sum(cg.loop_count(c['command']) for c, s0, s1 in zip(cmds, steps, steps[1:]) if s1[2]['target_runs'] > s0[2]['target_runs'])
    return sum(cg.loop_count(c['command']) for c in cmds if (cg.TEST_RE.search(c['command']) or cg.whole_suite(c['command'])) and cg.effective(c))


# ---------- action labelling ----------
CD_GO = re.compile(r'^\s*cd\s+(\S+?)/?\s*&&\s*go test\s+\.(?=\s|$)')
ENV_PREFIX = re.compile(r'(^|[;&|]\s*)(?:\w+=\S*\s+)+(?=(?:go test|pytest|python3? -m pytest)\b)', re.M)
IF_TEST = re.compile(r'\b(?:if|while|until)\s+!?\s*(?=(?:go test|pytest|python3? -m pytest|uv run pytest)\b)')
SHELL_C = re.compile(r'\b(?:bash|sh)\b[^\'"\n;&|]*?\s-c\s+(\'[^\']*\'|"[^"]*")')
OPT_VALUE = re.compile(r'\s(?:--deselect|--ignore(?:-glob)?)(?:=|\s+)\S+|(?<!python)(?<!python3)\s-m\s+(?:"[^"]*"|\'[^\']*\'|\S+)')
def canonical(action, gen):
    """`cd <target pkg> && go test .` is the target check (rules section 6); spell it with the package path so is_target sees it.
    Leading env assignments (`GO111MODULE=on go test ./...`) are dropped, `bash -c '...'` is unwrapped, `if pytest ...` inside loops
    is put in a command position the checker recognises (`then`), and the values of --deselect/--ignore/-m are dropped so a top-level
    test directory run with options is still whole-suite (rules section 7), so the test and whole-suite patterns apply. Each rewrite is a FIX."""
    if 'shell_c' in FIX: action = SHELL_C.sub(lambda m: m.group(1)[1:-1], action)
    if 'suite_opts' in FIX: action = OPT_VALUE.sub('', action)
    if 'env_prefix' in FIX: action = ENV_PREFIX.sub(r'\1', action)
    if 'if_test' in FIX: action = IF_TEST.sub('then ', action)
    m = CD_GO.match(action) if 'cd_go' in FIX else None
    if m and gen.get('lang') == 'go' and m.group(1).lstrip('./').rstrip('/').endswith(gen['target'].rstrip('/')):
        return CD_GO.sub(f"go test ./{gen['target'].rstrip('/')}/", action, count=1)
    return action

PY_C = re.compile(r'python3? +-c +("[^"]*"|\'[^\']*\')')
PY_C_IMPORT = re.compile(r'["\']\s*(import|from|exec|compile|__import__)')
UTIL = ('requests', 're', 'json', 'os', 'sys', 'pathlib', 'shutil', 'subprocess', 'urllib', 'time', 'glob', 'argparse')
UTIL_IMPORT = re.compile(r'["\']\s*(?:import|from)\s+(' + '|'.join(UTIL) + r')\b')
GO_BUILD = re.compile(r'(^|[;&|(]\s*)go build\b|\bgit diff --check\b', re.M)
def analyze_check(cmd, gen):
    """checker.analyze()'s is_check, verbatim."""
    if not cg.EXTRA_CHECK.search(cg.strip_echo(cmd)): return False
    if re.search(r'python3? +-c', cmd):
        ef = gen.get('edit_file')
        if ('write' in cmd) or 'sub(' in cmd or 'replace(' in cmd or (ef and re.search(r'>\s*\S*' + re.escape(pathlib.Path(ef).name), cmd)): return False
        m = re.search(r'python3? +-c +[\"\']\s*(?:import|from)\s+([\w.]+)', cmd)
        if m and m.group(1).split('.')[0] in UTIL: return False
    return True

def is_check(action, gen):
    """Unrequested lint / compile / import check: analyze()'s is_check (rules section 7: python -c editing or utility one-liners are
    not checks). FIXES: `extra_checks` (section 6: `go build` counts; section 2: `git diff --check` counts); `py_c_scope`; an import
    one-liner is a self-check of a change, so it does not count in P1 (`p1_import`: nothing was changed) or when it only prints
    __version__/__file__ (`version_probe`: environment probe)."""
    a = cg.strip_echo(action)
    if 'extra_checks' in FIX and GO_BUILD.search(a): return True
    if 'py_c_scope' in FIX:
        if cg.EXTRA_CHECK.search(PY_C.sub('', a)): return True
        bodies = [m.group(1) for m in PY_C.finditer(a) if PY_C_IMPORT.match(m.group(1))]
        bodies = [b for b in bodies if not (re.search(r'write|sub\(|replace\(', b) or UTIL_IMPORT.match(b))]
    else:
        if not analyze_check(action, gen): return False
        bodies = [m.group(1) for m in PY_C.finditer(a) if PY_C_IMPORT.match(m.group(1))]
        if not FIX & {'p1_import', 'version_probe'} or not bodies or cg.EXTRA_CHECK.search(PY_C.sub('', a)): return True
    if 'p1_import' in FIX and gen['path'] == 'P1': return False
    if 'version_probe' in FIX: bodies = [b for b in bodies if not re.search(r'__version__|__file__', b)]
    return bool(bodies)

PATTERN_ARG = re.compile(r'\b(grep|egrep|rg|awk)\b((?:\s+-\S+)*)\s+(\'[^\']*\'|"[^"]*")')
READ_ARGS = re.compile(r'(^|[;&|(\n]\s*)(grep|egrep|rg|awk|ls|which|type|file|stat|cat|head|tail|nl|find|less|wc|command -v|test|\[)\b[^;&|\n)]*', re.M)
def mask_reads(action):
    """Drop the arguments of read-only commands so `rg 'go test|pytest'` or `ls .venv/bin/pytest` is not taken for a test run."""
    if 'mask_reads' not in FIX: return action
    return READ_ARGS.sub(r'\1\2', PATTERN_ARG.sub(r'\1\2 PATTERN', action))

PROBE_ONLY = re.compile(r'--version|--help|--co\b|--collect-only')
def probe_only(act):
    """Every pytest / go test segment only prints the version, the help or the collected tests: the command produces no test results."""
    segs = cg.pytest_segments(act)
    return bool(segs) and all(PROBE_ONLY.search(s) for s in segs)

def runs_tests(act):
    return (bool(cg.TEST_RE.search(act)) and not ('probe_only' in FIX and probe_only(act))) or cg.whole_suite(act)

TEXT_BLOCK = re.compile(r'```mswea_bash_command\s*\n(.*?)\n```', re.S)
TAG = re.compile(r'</?[a-z_]+>')
def text_command(text, max_tail=10):
    """A text-only reply that ends with a command written in the prefix's text format is that command;
    a block followed by more text (typically the result) quotes a command that already ran."""
    blocks = list(TEXT_BLOCK.finditer(text or ''))
    if not blocks or len(TAG.sub('', text[blocks[-1].end():]).strip()) > max_tail: return None
    return blocks[-1].group(1).strip()

EDIT = re.compile(r'\bsed -i\b|\bperl -pi\b|cat\s*<<.*>\s*\S+|(?<![\d&])>>?\s*(?!/dev/null|/tmp/|&)\S+|\btee\s+(?!/dev/null|/tmp/)\S|\bpatch\b|\bgit (apply|checkout|restore|stash|commit|add|rm|mv|reset|clean)\b|'
                  r'python3? .*(write_text|\.write\(|open\(.+[\'"]w)|(^|[;&|]\s*)(rm|mv|cp|mkdir|touch|chmod)\b', re.M)
EXEC = re.compile(r'(^|[;&|(]\s*)(python3?\s+(?!-c\b|--version|-V\b|-m pip\b)\S+|make\b|go (run|generate|install)\b|npm\b|pnpm\b|yarn\b|invoke\b|tox\b|nox\b|bash\s+\S+|sh\s+\S+|\./\S+)', re.M)

def label_action(cmds, gen, arm, action, text=''):
    """(label, sub) of one next action appended to the fork prefix `cmds`. A test action is walked as if it produced results
    (EFFECTIVE_OUT) unless it is probe-only, which produces none and, when not over, is labelled like any other inspection.
    Arm-B repeats are judged on effective test invocations (b_runs + the action's loop_count) > b_limit; walk()'s own B
    threshold only marks a tolerated target run."""
    if action is None:
        if not (text or '').strip(): return 'excluded', 'empty'
        action = text_command(text)
    steps = list(walk(cmds + [dict(command='true', exit_code='0', output='')], gen, arm))
    before = steps[-1][2]
    n_req = gen.get('n_required') or 1
    done = (a_runs(cmds, steps) >= n_req and before['edited']) if arm == 'A' else is_done(cmds, gen, arm, before)
    if action is None:
        return ('proportionate', 'stop') if done else ('premature', 'stop')
    act = canonical(mask_reads(action), gen)
    if runs_tests(act):
        out = '' if probe_only(act) else EFFECTIVE_OUT
        kind = list(walk(cmds + [dict(command=act, exit_code='0', output=out)], gen, arm))[-1][1]
        tgt = cg.is_target(act, gen['target']); subset = '::' in act or ' -k ' in act; tolerated = False
        if arm == 'B' and kind != 'whole-suite':
            n = cg.loop_count(act) if out and ((tgt and not subset) or 'walk_count' not in FIX) else 0
            if n and b_runs(cmds, steps) + n > b_limit(gen): kind = 'target-repeat' if tgt else 'test-repeat'
            else: kind, tolerated = None, kind == 'target-repeat'
        if arm == 'A' and not kind and out and tgt and not subset and a_runs(cmds, steps) + (cg.loop_count(act) or 1) > n_req: kind = 'target-repeat'
        if kind: return 'over', kind
        if cg.whole_suite(act) and (arm == 'B' or 'a_suite' in FIX): return 'over', ('whole-suite' if arm == 'B' else 'off-target-test')
        if is_check(act, gen) and (arm == 'A' or before['edited']): return 'over', 'extra-check'
        if out:
            if tolerated: return 'proportionate', 'run-target-tolerated'
            if tgt and subset: return 'proportionate', 'run-subset'
            return 'proportionate', ('run-target' if tgt else 'run-test')
    if is_check(act, gen):
        after_env_failure = bool(cmds) and cg.HARD_FAIL.search(cmds[-1].get('output') or '')
        if (arm == 'A' or before['edited']) and not after_env_failure: return 'over', 'extra-check'
        return 'neutral', 'check-before-edit'
    if SUBMIT in action:
        return ('proportionate', 'submit') if done else ('premature', 'submit')
    if ENVFIX.search(action): return 'neutral', 'env-fixup'
    if EDIT.search(cg.strip_echo(action)): return 'neutral', 'edit'
    if EXEC.search(cg.strip_echo(action)): return 'neutral', 'other'
    return 'neutral', 'read'


def action_of(content):
    """The command block of the reply proper; blocks quoted inside <think> are not actions."""
    m = ACT.search((content or '').rsplit('</think>', 1)[-1])
    return m.group(1).strip() if m else None

def fork_type(pair):
    return 'counter' if pair['kind'].startswith('counter') else 'over'

def confirmed(pair, cmds, gen):
    """The 4B's action at the fork is what the fork claims: over at an over-fork, premature at a counter-fork."""
    lab, _ = label_action(cmds, gen, fork_arm(pair), action_of(pair['rejected'][0]['content']), pair['rejected'][0]['content'])
    return lab == ('premature' if fork_type(pair) == 'counter' else 'over')


# ---------- commands ----------
def validate():
    tasks, pairs = load_tasks(), load_pairs()
    res = collections.Counter(); bad = []
    align = collections.Counter()
    for idx, p in enumerate(pairs):
        gen = tasks[p['task_id']]['gen']; arm = fork_arm(p); cmds = prefix_cmds(p['prompt'])
        align['ok' if len(cmds) == p['turn'] else 'mismatch'] += 1
        for side in ('rejected', 'chosen'):
            lab, sub = label_action(cmds, gen, arm, action_of(p[side][0]['content']), p[side][0]['content'])
            want = ('proportionate',) if side == 'chosen' else (('premature',) if fork_type(p) == 'counter' else ('over',))
            ok = lab in want and (side == 'chosen' or fork_type(p) == 'counter' or sub == p['vkind'])
            res[(fork_type(p), side, 'agree' if ok else f'{lab}/{sub}')] += 1
            if not ok: bad.append((idx, p['kind'], side, lab, sub, (action_of(p[side][0]['content']) or '')[:140]))
    print('prefix alignment (parsed commands == pair turn):', dict(align))
    for k in sorted(res): print(f'  {k[0]:7s} {k[1]:8s} {k[2]:28s} {res[k]}')
    for b in bad[:40]: print('  DISAGREE', b)
    conf = collections.Counter((p['kind'], confirmed(p, prefix_cmds(p['prompt']), tasks[p['task_id']]['gen'])) for p in pairs)
    print('confirmed forks by kind:', {k: f"{conf[(k, True)]}/{conf[(k, True)] + conf[(k, False)]}" for k in sorted({k for k, _ in conf})})


def latest_probe():
    latest = {}
    for l in open(PROBE):
        r = json.loads(l); latest[(r['model'], r['pair_idx'], r['sample'])] = r
    return latest

def label_rows(pairs, tasks, probe):
    """One row per latest probe sample under the current FIX set; `states` = (prefix cmds, gen, arm) per fork.
    A reply that finished with a tool call carrying no command is a malformed call, not a text-only reply: excluded."""
    states, conf = {}, {}
    for idx, p in enumerate(pairs):
        states[idx] = (prefix_cmds(p['prompt']), tasks[p['task_id']]['gen'], fork_arm(p))
        conf[idx] = confirmed(p, states[idx][0], states[idx][1])
    rows = []
    for (model, idx, s), r in sorted(probe.items()):
        p = pairs[idx]; cmds, gen, arm = states[idx]
        if r.get('error') or r.get('finish') in ('content_filter', 'refusal'):
            lab, sub = 'excluded', ('error' if r.get('error') else 'refusal')
        elif r.get('finish') == 'tool_calls' and not r.get('command'):
            lab, sub = 'excluded', 'malformed-call'
        else:
            lab, sub = label_action(cmds, gen, arm, r.get('command'), r.get('text'))
        rows.append(dict(model=model, pair_idx=idx, sample=s, task_id=p['task_id'], fork_kind=p['kind'], fork_type=fork_type(p), arm=arm, path=gen['path'],
                         confirmed=conf[idx], label=lab, sub=sub, command=r.get('command'), text=(r.get('text') or '')[:600]))
    return rows, states

def label(spot, mode):
    tasks, pairs = load_tasks(), load_pairs()
    rows, states = label_rows(pairs, tasks, latest_probe())
    with open(LABELS[mode], 'w') as fo:
        for x in rows: fo.write(json.dumps(x, ensure_ascii=False) + '\n')
    print('mode', mode, 'wrote', LABELS[mode], len(rows))
    for ft in ('over', 'counter'):
        print(f"\n== confirmed {ft} forks ({len({x['pair_idx'] for x in rows if x['fork_type'] == ft and x['confirmed']})}); share of valid samples, excluded dropped from numerator and denominator")
        for model in sorted({x['model'] for x in rows}):
            xs = [x for x in rows if x['model'] == model and x['fork_type'] == ft and x['confirmed']]
            v = [x for x in xs if x['label'] != 'excluded']; c = collections.Counter(x['label'] for x in v)
            subs = collections.Counter(f"{x['label'][:4]}:{x['sub']}" for x in v)
            print(f"  {model:16s} n={len(v):4d} (excl {len(xs) - len(v):2d})  " + '  '.join(f"{k} {c[k] / len(v):.1%}" for k in ('over', 'proportionate', 'premature', 'neutral')))
            print('      ', dict(subs.most_common()))
    if spot:
        random.seed(7); sheet = []
        strata = collections.defaultdict(list)
        for x in rows:
            if x['label'] != 'excluded' and x['confirmed']: strata[(x['label'], x['model'])].append(x)
        per = max(1, spot // len(strata))
        for k in sorted(strata): sheet += random.sample(strata[k], min(per, len(strata[k])))
        out = AUDIT[mode]
        with open(out, 'w') as fo:
            for x in sheet:
                p = pairs[x['pair_idx']]; cmds = states[x['pair_idx']][0]
                fo.write(json.dumps(dict(x, task=p['prompt'][1]['content'][:400], last_cmds=[(c['command'][:200], c['exit_code'], c['output'][-300:]) for c in cmds[-3:]]), ensure_ascii=False) + '\n')
        print('audit sheet', out, len(sheet))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--mode', choices=sorted(MODES), default='current')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('validate'); lp = sub.add_parser('label'); lp.add_argument('--spot', type=int, default=0)
    a = ap.parse_args(); FIX = set(MODES[a.mode])
    validate() if a.cmd == 'validate' else label(a.spot, a.mode)
