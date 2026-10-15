#!/usr/bin/env python3
"""Run-level summary of a runs root (no judging): completion, oracle pass, duration, commands, by class and arm; A-B command deltas."""
import json, collections, statistics, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]; RR=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'work/runs')
R=[json.loads(l) for l in open(RR/'runs.jsonl')]
tasks={json.loads(open(f).read())['task_id']:json.loads(open(f).read()) for f in ROOT.glob('data/tasks/*/*/task.json')}
def med(xs): xs=sorted(xs); return xs[len(xs)//2] if xs else None
print(f"runs {len(R)}  tasks {len({r['task_id'] for r in R})}  arms A={sum(r['arm']=='A' for r in R)} B={sum(r['arm']=='B' for r in R)}")
print('exit_status', dict(collections.Counter(r['exit_status'] for r in R)))
print('oracle pass', sum(1 for r in R if r['oracle_rc']==0), '/', len(R))
print('duration s: median', med([r['duration'] for r in R]), 'p90', sorted(r['duration'] for r in R)[int(len(R)*.9)], 'max', max(r['duration'] for r in R))
print('n_commands: median', med([r['n_commands'] for r in R]), 'max', max(r['n_commands'] for r in R))
print('\n| class | arm | runs | submitted | oracle pass | median cmds | median s |'); print('|---|---|---|---|---|---|---|')
for cls in sorted({r['cls'] for r in R}):
    for arm in 'AB':
        rs=[r for r in R if r['cls']==cls and r['arm']==arm]
        print(f"| {cls} | {arm} | {len(rs)} | {sum(r['exit_status']=='Submitted' for r in rs)} | {sum(r['oracle_rc']==0 for r in rs)} | {med([r['n_commands'] for r in rs])} | {med([r['duration'] for r in rs])} |")
# metrics-based: tokens, files changed, diff size
M=[]
for r in R:
    m=json.loads(open(ROOT/r['dir']/'metrics.json').read()); m['cls']=r['cls']; m['arm']=r['arm']; m['task_id']=r['task_id']; M.append(m)
print('\ntokens per run: input median', med([m['usage']['input_tokens'] for m in M]), 'output median', med([m['usage']['output_tokens'] for m in M]), 'length truncations total', sum(m['usage']['length_truncations'] for m in M), 'format errors total', sum(m['format_errors'] for m in M))
print('diff lines added median', med([m['diff_added'] for m in M]), 'files changed median', med([m['n_files_changed'] for m in M]))
# A-B command delta per task
by=collections.defaultdict(dict)
for r in R: by[r['task_id']][r['arm']]=r
deltas=[]
for tid,d in by.items():
    if 'A' in d and 'B' in d: deltas.append((d['A']['n_commands']-d['B']['n_commands'], tid, d['A']['n_commands'], d['B']['n_commands'], tasks[tid]['class'], tasks[tid]['sub']))
deltas.sort()
print('\nlargest A-B command deltas (negative = more in B):'); [print(' ', x) for x in deltas[:8]]; print(' ...'); [print(' ', x) for x in deltas[-5:]]
print('\nmedian A-B command delta by class:', {c: med([d[0] for d in deltas if d[4]==c]) for c in sorted({d[4] for d in deltas})})
print('runs failing the oracle:'); [print(' ', r['run_id'], r['exit_status']) for r in R if r['oracle_rc']!=0]
