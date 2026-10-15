#!/usr/bin/env python3
"""Turn-level over-defense pairs, using the checker semantics (effective runs, env fixes, last-edit policy) for arm A
(scope stated) and arm B (proportionality). For each oracle-passing run, find the FIRST violating command; rejected = that
assistant turn; chosen = on-policy resample (replay context, n=12, t=0.6, first compliant action), fallback = sibling
compliant submit turn. usage: extract.py --runs work/runs --ports 8000 --out work/pairs/over [--max-per-task 4]"""
import argparse, json, glob, re, collections, pathlib, requests, random, itertools, importlib.util as u, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parents[2]
s = u.spec_from_file_location('cg', ROOT/'src/checker/checker.py'); cg = u.module_from_spec(s); s.loader.exec_module(cg)
SUBMIT = 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'
random.seed(5)
class _Suite:
    def search(self, cmd): return cg.whole_suite(cmd)
SUITE = _Suite()
ENVFIX = re.compile(r'\b(pip install|uv pip|uv sync|uv add|poetry install|apt-get|apt install|npm install|go get|go mod download)\b')
READ = re.compile(r'^\s*(cat|sed -n|grep|head|tail|less|ls|pwd|find|git (status|log|diff|show)|wc|echo|printf|which|type)\b')

def action_of(text):
    m = re.search(r'```mswea_bash_command\s*\n(.*?)\n```', text or '', re.S)
    return m.group(1).strip() if m else None
def full_completion(msg):
    r = msg.get('reasoning_content') or ''; c = msg.get('content') or ''
    return (f'<think>\n{r}\n</think>\n\n{c}') if r else c

def walk(cmds, gen, arm):
    """Yield per-command state: (idx, kind_or_None, state_before) following checker semantics.
    state = dict(target_runs=<effective full target runs so far (post-last-edit for P4)>, edited=<bool>, any_test=<bool>)"""
    target = gen['target']; n_req = gen.get('n_required') or 1; edit_file = gen.get('edit_file'); path = gen['path']
    last_edit = None
    if path == 'P4' and edit_file:
        edits = [i for i, c in enumerate(cmds) if edit_file in c['command'] and not re.match(r'\s*(cat|sed -n|grep|head|tail|less|git diff|git show|git checkout|git restore|git stash|wc|ls)\b', c['command'].strip())]
        last_edit = edits[-1] if edits else None
    tinv = [i for i, c in enumerate(cmds) if cg.TEST_RE.search(c['command'])]
    def eff(i):
        c = cmds[i]
        if not cg.effective(c):
            return bool(re.search(r'(>|\| *tee)\s*\S+', c['command'])) and str(c.get('exit_code')) in ('0', '1')
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

def compliant(action, gen, before, arm):
    """Chosen must be a strong contrast: submit (if requirements met) or run the target once (if not yet)."""
    if action is None or cg.EXTRA_CHECK.search(cg.strip_echo(action)) or SUITE.search(action): return False
    n_req = gen.get('n_required') or 1; tgt = cg.is_target(action, gen['target']); is_test = bool(cg.TEST_RE.search(action))
    if SUBMIT in action: return before['target_runs'] >= n_req and before['edited']
    if is_test:
        if arm == 'A': return tgt and '::' not in action and before['target_runs'] < n_req
        return before['target_runs'] < max(2, n_req) and (tgt or (not SUITE.search(action)))
    return False

def harvest(ctx_msgs, port, n=12):
    body = dict(model='Qwen3.5-4B', messages=ctx_msgs, n=n, temperature=0.6, top_p=0.95, top_k=20, max_tokens=4000, chat_template_kwargs={'enable_thinking': True})
    r = requests.post(f'http://localhost:{port}/v1/chat/completions', json=body, timeout=900); r.raise_for_status()
    return [dict(content=ch['message'].get('content') or '', reasoning_content=ch['message'].get('reasoning_content') or '') for ch in r.json()['choices']]

def load_run(r):
    rd = ROOT/r['dir']
    traj = json.loads((rd/'trajectory.json').read_text()); cmds = [json.loads(l) for l in (rd/'commands.jsonl').read_text().splitlines()]
    return traj, cmds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', required=True); ap.add_argument('--ports', default='8000'); ap.add_argument('--max-per-task', type=int, default=4)
    ap.add_argument('--out', default='work/pairs/over'); ap.add_argument('--workers', type=int, default=16); ap.add_argument('--no-harvest', action='store_true'); ap.add_argument('--arms', default='AB')
    a = ap.parse_args(); ports = [int(p) for p in a.ports.split(',')]
    tasks = {json.load(open(f))['task_id']: json.load(open(f)) for f in glob.glob(str(ROOT/'data/tasks/*/*/task.json'))}
    outd = ROOT/a.out; outd.mkdir(parents=True, exist_ok=True)
    runs = [json.loads(l) for rr in a.runs.split(',') for l in open(ROOT/rr/'runs.jsonl')]
    runs = [r for r in runs if r['task_id'] in tasks and tasks[r['task_id']]['gen']['path'] in ('P1', 'P4') and r.get('oracle_rc') == 0 and not tasks[r['task_id']]['gen'].get('excluded') and r['arm'] in a.arms]
    stats = collections.Counter(); sib = collections.defaultdict(list); cands = []
    for r in runs:
        t = tasks[r['task_id']]; gen = t['gen']; arm = r['arm']
        try: traj, cmds = load_run(r)
        except Exception: stats['skip_load'] += 1; continue
        msgs = traj['messages']; amap = [i for i, m in enumerate(msgs) if m.get('role') == 'assistant' and (m.get('extra') or {}).get('actions')]
        if len(amap) != len(cmds): stats['skip_align'] += 1; continue
        steps = list(walk(cmds, gen, arm)); first = next(((i, k, b) for i, k, b in steps if k), None)
        key = (r['task_id'], arm)
        if first is None:
            stats[f'clean_{arm}'] += 1
            for i, m in enumerate(msgs):
                if m.get('role') == 'assistant' and SUBMIT in (action_of(m.get('content')) or ''): sib[key].append(full_completion(m))
            continue
        stats[f'viol_{arm}_{first[1]}'] += 1
        cands.append((r, gen, arm, msgs, amap, cmds, first))
    per_task = collections.Counter(); pairs = []
    random.shuffle(cands)
    def build(item, port):
        r, gen, arm, msgs, amap, cmds, (vidx, vkind, before) = item
        mi = amap[vidx]; ctx = [{'role': m['role'], 'content': m['content']} for m in msgs[:mi] if m.get('role') in ('system', 'user', 'assistant')]
        chosen = None; source = None
        if not a.no_harvest:
            try:
                for c in harvest(ctx, port):
                    if compliant(action_of(c['content']), gen, before, arm): chosen = full_completion(c); source = 'on-policy'; break
            except Exception as e: return ('harvest_error', None)
        if chosen is None and before['target_runs'] >= (gen.get('n_required') or 1) and before['edited'] and sib.get((r['task_id'], arm)):
            chosen = random.choice(sib[(r['task_id'], arm)]); source = 'sibling-submit'
        if chosen is None: return ('no_compliant', None)
        return ('pair', dict(task_id=r['task_id'], run_id=r['run_id'], arm=arm, vkind=vkind, turn=vidx, chosen_source=source, kind=f'overguard-{arm}-{vkind}',
                             prompt=ctx, chosen=[{'role': 'assistant', 'content': chosen}], rejected=[{'role': 'assistant', 'content': full_completion(msgs[mi])}]))
    todo = []
    for item in cands:
        k = (item[0]['task_id'], item[2])
        if per_task[k] >= a.max_per_task: stats['skip_cap'] += 1; continue
        per_task[k] += 1; todo.append(item)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(build, item, ports[i % len(ports)]) for i, item in enumerate(todo)]
        for f in futs:
            st, p = f.result(); stats[st] += 1
            if p: pairs.append(p)
    with open(outd/'dpo_pairs.jsonl', 'w') as fo:
        for p in pairs: fo.write(json.dumps(p, ensure_ascii=False) + '\n')
    json.dump(dict(stats=dict(stats), n_pairs=len(pairs), tasks=len({p['task_id'] for p in pairs}), by_kind=dict(collections.Counter(p['kind'] for p in pairs)),
                   by_source=dict(collections.Counter(p['chosen_source'] for p in pairs))), open(outd/'pair_stats.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(stats), ensure_ascii=False)); print('pairs', len(pairs), 'tasks', len({p['task_id'] for p in pairs}), dict(collections.Counter(p['kind'] for p in pairs)))
if __name__ == '__main__': main()
