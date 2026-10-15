#!/usr/bin/env python3
"""Sensitivity of fork labels to forks.py's mode: current vs strict, plus one-flag ablations (each FIX that only current has
dropped from current / added to strict; each FIX both modes keep dropped from strict = `pure`) to attribute every label
difference to the deviation that causes it.
Shares are over valid samples (excluded dropped from numerator and denominator); decisive = over + proportionate + premature.
A fork prefix is dirty when the checker already flags a command in it (walk() kinds; arm B also b_verdict()'s whole-suite
attempt and effective test runs > max(2, n_required + 1)), i.e. the fork is not the 4B's first violation under the final checker.
usage: fork_sensitivity.py [--out results/fork_sensitivity.json]"""
import argparse, collections, json, pathlib
import forks as fc
cg = fc.cg

LABS = ('over', 'proportionate', 'premature', 'neutral')
METRICS = LABS + ('over_decisive', 'forks_any_over')

def run(fix):
    fc.FIX = set(fix)
    rows, _ = fc.label_rows(PAIRS, TASKS, PROBE)
    return rows

def key(x): return (x['model'], x['pair_idx'], x['sample'])

def confirmed_by_kind(rows):
    seen = {x['pair_idx']: (x['fork_kind'], x['confirmed']) for x in rows}
    c = collections.Counter(seen.values())
    return {k: (c[(k, True)], c[(k, True)] + c[(k, False)]) for k in sorted({k for k, _ in c})}

def shares(v):
    c = collections.Counter(x['label'] for x in v); dec = c['over'] + c['proportionate'] + c['premature']
    forks = collections.defaultdict(bool)
    for x in v: forks[x['pair_idx']] |= x['label'] == 'over'
    return dict(n=len(v), forks=len(forks), **{k: c[k] / len(v) for k in LABS}, over_decisive=c['over'] / dec if dec else 0.0,
                forks_any_over=sum(forks.values()) / len(forks))

GROUPS = (('A', lambda x: x['arm'] == 'A'), ('B', lambda x: x['arm'] == 'B'),
          ('B-ws', lambda x: x['fork_kind'] == 'overguard-B-whole-suite'), ('B-rep', lambda x: x['fork_kind'] == 'overguard-B-target-repeat'))
def over_table(rows, keep=lambda x: True):
    """Confirmed over-forks, per (model, group): label shares, over among decisive, share of forks with >=1 over sample."""
    out = {}
    for m in sorted({x['model'] for x in rows}):
        for g, sel in GROUPS:
            v = [x for x in rows if x['model'] == m and x['fork_type'] == 'over' and x['confirmed'] and x['label'] != 'excluded' and sel(x) and keep(x)]
            if v: out[(m, g)] = shares(v)
    return out

def counter_table(rows):
    out = {}
    for m in sorted({x['model'] for x in rows}):
        v = [x for x in rows if x['model'] == m and x['fork_type'] == 'counter' and x['confirmed'] and x['label'] != 'excluded']
        out[m] = shares(v)
    return out

def diff(a, b, field='label'):
    bk = {key(x): x for x in b}
    return {key(x) for x in a if x[field] != bk[key(x)][field]}

def dirty(pair):
    gen = TASKS[pair['task_id']]['gen']; arm = fc.fork_arm(pair)
    cmds = [dict(c, command=fc.mask_reads(c['command'])) for c in fc.prefix_cmds(pair['prompt'])]
    if any(k for _, k, _ in fc.walk(cmds, gen, arm)): return 'walk'
    if arm == 'B':
        res = lambda c: cg.RESULT.search(cg.ANSI.sub('', c.get('output') or ''))
        if any(cg.whole_suite(c['command']) and not (cg.MECH.search(c.get('output') or '') and not res(c)) for c in cmds): return 'b_verdict-suite'
        if sum(cg.loop_count(c['command']) for c in cmds if (cg.TEST_RE.search(c['command']) or cg.whole_suite(c['command'])) and cg.effective(c)) > fc.b_limit(gen): return 'b_verdict-runs'
    return None

def print_over(title, tabs):
    names = list(tabs)
    print(f'\n{title}  [' + ' | '.join(names) + ']')
    print(f"  {'model':16s} {'grp':5s} {'n':>14s} {'forks':>12s} " + ' '.join(f'{h:>22s}' for h in ('over', 'proportionate', 'premature', 'neutral', 'over/decisive', 'forks>=1 over')))
    for k in tabs[names[0]]:
        cells = [tabs[nm].get(k) for nm in names]
        fmt = lambda h: '|'.join(f"{c[h]:5.1%}" if c else '  -  ' for c in cells)
        print(f"  {k[0]:16s} {k[1]:5s} {'|'.join(str(c['n']) if c else '-' for c in cells):>14s} {'|'.join(str(c['forks']) if c else '-' for c in cells):>12s} "
              + ' '.join(f'{fmt(h):>22s}' for h in METRICS))

def main():
    global PAIRS, TASKS, PROBE
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=str(fc.WORK / 'results/fork_sensitivity.json')); a = ap.parse_args()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    PAIRS, TASKS, PROBE = fc.load_pairs(), fc.load_tasks(), fc.latest_probe()
    cur, strict = fc.MODES['current'], fc.MODES['strict']
    only, shared = sorted(cur - strict), sorted(strict)
    R = {'current': run(cur), 'strict': run(strict), 'pure': run(strict - set(shared))}
    for f in only: R[f'current-{f}'] = run(cur - {f}); R[f'strict+{f}'] = run(strict | {f})
    for f in shared: R[f'current-{f}'] = run(cur - {f}); R[f'strict-{f}'] = run(strict - {f})
    C, S, P = R['current'], R['strict'], R['pure']

    print('(i) confirmed forks by kind   current   strict   pure (strict without', ', '.join(shared) + ')')
    cc, cs, cp = confirmed_by_kind(C), confirmed_by_kind(S), confirmed_by_kind(P)
    for k in cc: print(f'  {k:30s} {cc[k][0]:4d}/{cc[k][1]:<4d} {cs[k][0]:4d}/{cs[k][1]:<4d} {cp[k][0]:4d}/{cp[k][1]:<4d}')
    print_over('(ii) confirmed over-forks, share of valid samples', {'current': over_table(C), 'strict': over_table(S), 'pure': over_table(P)})
    kc, ks, kp = counter_table(C), counter_table(S), counter_table(P)
    print('\n(iii) confirmed counter forks  [current | strict | pure]')
    for m in kc:
        print(f"  {m:16s} n={kc[m]['n']}|{ks[m]['n']}|{kp[m]['n']}  " + '  '.join(f"{h} {kc[m][h]:.1%}|{ks[m][h]:.1%}|{kp[m][h]:.1%}" for h in LABS))

    D = diff(C, S); Dc = diff(C, S, 'confirmed')
    both = {key(x) for x in C if x['confirmed']} & {key(x) for x in S if x['confirmed']}
    ck = {key(x): x for x in C}; sk = {key(x): x for x in S}
    print(f'\n(iv) samples whose label differs current vs strict: {len(D)} / {len(C)} (at forks confirmed in both modes: {len(D & both)});'
          f' samples whose fork confirmation differs: {len(Dc)}')
    trans = collections.Counter((ck[k]['fork_type'], ck[k]['arm'], ck[k]['label'], sk[k]['label']) for k in D)
    for t, n in trans.most_common(): print(f'    {n:4d}  {t[0]:7s} {t[1]}  current {t[2]:13s} -> strict {t[3]}')
    print('  one-flag ablations: label flips (all samples / at forks confirmed in current); fork-confirmation flips')
    attr, flips = {}, {}
    for f in only + shared:
        alt = R[f'strict+{f}'] if f in only else R[f'strict-{f}']
        rm, ad = diff(C, R[f'current-{f}']), diff(S, alt)
        flips[f] = (rm | ad) & D
        attr[f] = dict(in_strict=f in shared, drop_from_current=len(rm), drop_at_confirmed=len({k for k in rm if ck[k]['confirmed']}),
                       toggle_in_strict=len(ad), in_mode_diff=len(flips[f]), confirm_flips_current=len(diff(C, R[f'current-{f}'], 'confirmed')),
                       confirm_flips_strict=len(diff(S, alt, 'confirmed')))
        print(f"    {f:17s} {'(both modes)' if f in shared else '':12s} drop from current {len(rm):4d} / {attr[f]['drop_at_confirmed']:4d}; "
              f"{'drop from' if f in shared else 'add to'} strict {len(ad):4d}; in current-vs-strict diff {len(flips[f]):4d}; "
              f"confirmation flips {attr[f]['confirm_flips_current']}/{attr[f]['confirm_flips_strict']}")
    expl = collections.Counter(len([f for f in only if k in flips[f]]) for k in D)
    print('  current-vs-strict differences explained by exactly one flag:', expl.get(1, 0), ' by several:', sum(v for n, v in expl.items() if n > 1),
          ' by none alone:', expl.get(0, 0))

    dmap = {i: dirty(p) for i, p in enumerate(PAIRS)}
    for nm, rows in (('current', C), ('strict', S)):
        conf = {x['pair_idx']: (x['fork_kind'], x['confirmed']) for x in rows}
        dc = collections.Counter((conf[i][0], dmap[i]) for i in conf if conf[i][1] and dmap[i])
        print(f'\n(v) {nm}: confirmed forks with a dirty prefix:', dict(dc))
    print_over('    confirmed over-forks with a clean prefix only', {'current': over_table(C, lambda x: not dmap[x['pair_idx']]), 'strict': over_table(S, lambda x: not dmap[x['pair_idx']])})

    json.dump(dict(confirmed=dict(current=cc, strict=cs, pure=cp),
                   over={nm: {f'{k[0]}|{k[1]}': v for k, v in over_table(R[nm]).items()} for nm in ('current', 'strict', 'pure')},
                   counter=dict(current=kc, strict=ks, pure=kp), n_diff=len(D), n_diff_both_confirmed=len(D & both), attribution=attr,
                   transitions={'|'.join(t): n for t, n in trans.items()}, dirty={i: d for i, d in dmap.items() if d}), open(a.out, 'w'), indent=1)
    print('wrote', a.out)

if __name__ == '__main__': main()
