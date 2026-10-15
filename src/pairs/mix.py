#!/usr/bin/env python3
"""Mix over-defense pairs with skipped-check pairs: over-defense pairs deduplicated by (run, turn) and capped at `--cap`
per (task, arm); skipped-check pairs subsampled to `--counter-ratio` x the over-defense count, edit-and-verify first.
usage: mix.py --over work/pairs/over/dpo_pairs.jsonl[,...] --counter work/pairs/counter_pairs.jsonl [--out work/pairs/mix]"""
import json, random, collections, argparse, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]; random.seed(9)
ap = argparse.ArgumentParser()
ap.add_argument('--over', default='work/pairs/over/dpo_pairs.jsonl'); ap.add_argument('--counter', default='work/pairs/counter_pairs.jsonl')
ap.add_argument('--out', default='work/pairs/mix'); ap.add_argument('--counter-ratio', type=float, default=0.6); ap.add_argument('--cap', type=int, default=4)
a = ap.parse_args()
def load(p): return [json.loads(l) for l in open(ROOT/p)] if (ROOT/p).exists() else []
over = [p for f in a.over.split(',') for p in load(f)]
seen = set(); dedup = []
for p in over:
    k = (p['run_id'], p['turn'])
    if k in seen: continue
    seen.add(k); dedup.append(p)
random.shuffle(dedup); per = collections.Counter(); over_sel = []
for p in dedup:
    k = (p['task_id'], p['arm'])
    if per[k] >= a.cap: continue
    per[k] += 1; over_sel.append(p)
counter = load(a.counter); random.shuffle(counter)
p4 = [c for c in counter if c['kind'] == 'counter-P4']; p1 = [c for c in counter if c['kind'] != 'counter-P4']
n_counter = int(a.counter_ratio * len(over_sel)); counter_sel = (p4 + p1)[:n_counter]
mix = over_sel + counter_sel; random.shuffle(mix)
out = ROOT/a.out; out.mkdir(parents=True, exist_ok=True)
with open(out/'dpo_pairs.jsonl', 'w') as f:
    for p in mix: f.write(json.dumps(p, ensure_ascii=False) + '\n')
stats = dict(over_raw=len(over), over_dedup=len(dedup), over_selected=len(over_sel), counter_selected=len(counter_sel), total=len(mix),
             tasks=len({p['task_id'] for p in mix}), by_kind=dict(collections.Counter(p['kind'] for p in mix)), by_source=dict(collections.Counter(p.get('chosen_source') for p in over_sel)))
json.dump(stats, open(out/'mix_stats.json', 'w'), ensure_ascii=False, indent=1); print(json.dumps(stats, ensure_ascii=False))
