#!/usr/bin/env python3
"""Held-out comparison: per (arm, path, lang) n / done / over / over-rate / submit-only / med cmds, for several runs roots.
Arm B has no stated scope: 'over' there = proportionality flags only (whole-suite, >2 target runs, extra checks, rollback).
usage: compare.py work/runs_base [work/runs_forkdpo ...]"""
import json, sys, glob, collections, pathlib, importlib.util as u
ROOT = pathlib.Path(__file__).resolve().parents[2]
s = u.spec_from_file_location('cg', ROOT/'src/checker/checker.py'); cg = u.module_from_spec(s); s.loader.exec_module(cg)
tasks = {json.load(open(f))['task_id']: json.load(open(f)) for f in glob.glob(str(ROOT/'data/tasks/*/*/task.json'))}
rows = collections.defaultdict(list)
for rr in sys.argv[1:]:
    for r in map(json.loads, open(ROOT/rr/'runs.jsonl')):
        t = tasks.get(r['task_id'])
        if not t or t['gen']['path'] not in ('P1', 'P4'): continue
        a = cg.analyze(ROOT/r['dir'], t)
        if r['arm'] == 'A': over = a['over']; done = a['task_done']
        else: bv = cg.b_verdict(ROOT/r['dir'], t, a); over = bv['over']; done = bv['task_done']
        rows[(r['arm'], t['gen']['path'], t['gen'].get('lang', 'py'), rr)].append(dict(done=done, over=bool(over), so=(not a['task_done'] and a['n_cmds'] <= 1), n=a['n_cmds'], oracle=a['oracle_rc'] == 0, blocked=a.get('env_blocked', False)))
print(f"{'arm':3s} {'path':4s} {'lang':4s} {'model':22s} {'n':>4s} {'oracle':>6s} {'done':>5s} {'over':>5s} {'rate':>6s} {'submit_only':>11s} {'env_blk':>7s} {'med_cmds':>8s}")
for k in sorted(rows):
    rs = rows[k]
    print(f"{k[0]:3s} {k[1]:4s} {k[2]:4s} {k[3]:22s} {len(rs):4d} {sum(x['oracle'] for x in rs):6d} {sum(x['done'] for x in rs):5d} {sum(x['over'] for x in rs):5d} {sum(x['over'] for x in rs)/len(rs):6.3f} {sum(x['so'] for x in rs):11d} {sum(x['blocked'] for x in rs):7d} {sorted(x['n'] for x in rs)[len(rs)//2]:8d}")
for arm in 'AB':
    for rr in sys.argv[1:]:
        rs = [x for k, v in rows.items() if k[0] == arm and k[3] == rr for x in v]
        if rs: print(f"TOTAL {arm} {rr:22s} n={len(rs)} done={sum(x['done'] for x in rs)} over={sum(x['over'] for x in rs)} rate={sum(x['over'] for x in rs)/len(rs):.3f} submit_only={sum(x['so'] for x in rs)}")
