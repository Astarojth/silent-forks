#!/usr/bin/env python3
"""Skipped-check pairs from clean sampling runs:
  P1  : state 0 (system+task)      chosen = model's real first action (runs the target test)      rejected = a sibling submit message
  P4  : state before first target run (edit done) chosen = the real 'run target test' turn      rejected = a sibling submit message
Writes work/pairs/counter_pairs.jsonl. usage: counter.py --runs work/runs [--per-task 2]"""
import json, glob, re, random, collections, pathlib, argparse, importlib.util
ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ex', ROOT/'src/pairs/extract.py'); ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
LINT_RE = re.compile(r'\b(ruff|flake8|mypy|black|pylint|golangci-lint|go vet|isort)\b')
random.seed(5)

def violating(cmd, target, prior_target, required):
    if LINT_RE.search(ex.cg.strip_echo(cmd)): return 'lint'
    if ex.cg.TEST_RE.search(cmd):
        if not ex.cg.is_target(cmd, target): return 'off-target-test'
        if prior_target >= required: return 'target-repeat'
    return None

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--per-task', type=int, default=2); ap.add_argument('--runs', default='work/runs'); ap.add_argument('--out', default='work/pairs/counter_pairs.jsonl'); ap.add_argument('--arm', default='A'); a = ap.parse_args()
    tasks = {json.load(open(f))['task_id']: json.load(open(f)) for f in glob.glob(str(ROOT/'data/tasks/*/*/task.json'))}
    runs = [json.loads(l) for rr in a.runs.split(',') for l in open(ROOT/rr/'runs.jsonl')]
    runs = [r for r in runs if r.get('arm', 'A') == a.arm and not tasks.get(r['task_id'], {}).get('gen', {}).get('excluded')]
    clean = collections.defaultdict(list); sib = collections.defaultdict(list)
    for r in runs:
        t = tasks.get(r['task_id'])
        if not t or r.get('oracle_rc') != 0 or t['gen']['path'] not in ('P1','P4'): continue
        try:
            traj = json.loads((ROOT/r['dir']/'trajectory.json').read_text()); cmds = [json.loads(l)['command'] for l in (ROOT/r['dir']/'commands.jsonl').read_text().splitlines()]
        except Exception: continue
        gen = t['gen']; target = gen.get('target',''); required = gen.get('n_required') or 1
        if any(violating(c, target, sum(1 for d in cmds[:i] if ex.cg.is_target(d, target) and ex.cg.TEST_RE.search(d)), required) for i, c in enumerate(cmds)): continue
        if not any(ex.cg.is_target(c, target) and ex.cg.TEST_RE.search(c) for c in cmds): continue   # must have actually run the target
        clean[r['task_id']].append((traj['messages'], cmds))
        for m in traj['messages']:
            if m.get('role') == 'assistant' and ex.SUBMIT in (ex.action_of(m.get('content')) or ''): sib[r['task_id']].append(ex.full_completion(m))
    out = []; stats = collections.Counter()
    for tid, lst in clean.items():
        t = tasks[tid]; gen = t['gen']; target = gen['target']
        random.shuffle(lst)
        for msgs, cmds in lst[:a.per_task]:
            amap = [i for i, m in enumerate(msgs) if m.get('role') == 'assistant' and (m.get('extra') or {}).get('actions')]
            if len(amap) != len(cmds) or not sib.get(tid): stats['skip'] += 1; continue
            # the turn that first runs the target test
            k = next((i for i, c in enumerate(cmds) if ex.cg.is_target(c, target) and ex.cg.TEST_RE.search(c)), None)
            if k is None: continue
            if gen['path'] == 'P4' and not any(gen.get('edit_file','') in c for c in cmds[:k]): stats['p4_verify_before_edit'] += 1; continue
            mi = amap[k]
            ctx = [{'role': m['role'], 'content': m['content']} for m in msgs[:mi] if m.get('role') in ('system','user','assistant')]
            out.append(dict(task_id=tid, kind='counter-'+gen['path'], turn=k, chosen_source='on-policy', prompt=ctx,
                            chosen=[{'role':'assistant','content': ex.full_completion(msgs[mi])}],
                            rejected=[{'role':'assistant','content': random.choice(sib[tid])}]))
            stats['pair_'+gen['path']] += 1
    outp = ROOT/a.out; outp.parent.mkdir(exist_ok=True, parents=True)
    with open(outp,'w') as fo:
        for p in out: fo.write(json.dumps(p, ensure_ascii=False)+'\n')
    print(dict(stats), 'counter pairs:', len(out), 'tasks:', len({p['task_id'] for p in out}))
if __name__ == '__main__': main()
