#!/usr/bin/env python3
"""Progress and spend of the e2e run from local files only (never calls the API).
usage: status.py [--samples N] [--log N]"""
import argparse, json, os, statistics, subprocess, time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('FORKDPO_E2E_ROOT', REPO / 'work' / 'e2e')); RES = ROOT / 'results'
MODELS = ['deepseek-flash', 'glm-5.3', 'claude-opus-5-5', 'gpt-6.1-sol']
FINAL = {'Submitted', 'LimitsExceeded', 'RepeatedFormatError', 'Refusal'}
N_TASKS, N_ARMS = 48, 2


def jl(p):
    out = []
    if p.exists():
        for l in open(p):
            try: out.append(json.loads(l))
            except Exception: pass
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--samples', default='1', help='samples per model, e.g. 1 or ds=2,gl=2')
    ap.add_argument('--log', type=int, default=8); a = ap.parse_args()
    samples = dict.fromkeys(MODELS, 1)
    if '=' in a.samples:
        tag = {'ds': 'deepseek-flash', 'gl': 'glm-5.3', 'op': 'claude-opus-5-5', 'gp': 'gpt-6.1-sol'}
        for kv in a.samples.split(','):
            k, v = kv.split('='); samples[tag.get(k, k)] = int(v)
    else:
        samples = dict.fromkeys(MODELS, int(a.samples))
    plan = json.loads((RES / 'plan.json').read_text()) if (RES / 'plan.json').exists() else {}
    plan_total = plan.get('per_model_total') or {}
    if plan: print(f"plan: phase={plan.get('phase')} samples={plan.get('samples')} tasks={plan.get('n_tasks')} started={plan.get('started')}")
    procs = subprocess.run(['pgrep', '-af', 'e2e.py'], capture_output=True, text=True).stdout.strip().splitlines()
    procs = [p for p in procs if 'pgrep' not in p]
    cont = subprocess.run(['docker', 'ps', '--filter', 'name=forkdpo-e2e-', '--format', '{{.Names}}\t{{.RunningFor}}'], capture_output=True, text=True).stdout.strip().splitlines()
    g = json.loads((RES / 'breakers.json').read_text()) if (RES / 'breakers.json').exists() else {}
    latest = {}
    for r in jl(RES / 'runs.jsonl'): latest[r['key']] = r
    reqs = jl(RES / 'requests.jsonl')
    pids = [p.split()[0] for p in procs if 'python3' in p]
    print(f"== {time.strftime('%Y-%m-%d %H:%M:%S')}  runner: {'RUNNING pid ' + ','.join(pids) if pids else 'not running'}"
          f"  containers: {len(cont)}  STOP file: {'yes' if (ROOT / 'STOP').exists() else 'no'}")
    if (ROOT / 'STATUS').exists(): print('STATUS: ' + (ROOT / 'STATUS').read_text().splitlines()[0])
    spent = g.get('spent_usd', sum(r.get('cost') or 0 for r in reqs))
    ledger = sum(r.get('cost') or 0 for r in reqs) + sum(float(s.get('unrecorded_usd') or 0) for s in (g.get('models') or {}).values())
    print(f"spend ${max(spent, ledger):.2f} (ledger ${ledger:.2f}, guard ${spent:.2f}) of stop-at ${g.get('stop_at_usd', 185):.0f} / cap ${g.get('cap_usd', 200):.0f}; "
          f"in-flight ${g.get('inflight_usd', 0):.2f}; stop_reason={g.get('stop_reason')}; requests={len(reqs)}")
    hdr = f"{'model':<16} {'done':>9} {'subm':>4} {'lim':>3} {'ref':>3} {'fail':>4} {'orc0':>4} {'$spent':>7} {'cap':>4} {'$/run':>6} {'p90':>6} {'proj':>7} {'medcmd':>6} {'med_s':>6} {'act':>3}  breaker"
    print(hdr)
    proj_total = 0.0
    for m in MODELS:
        rs = [r for r in latest.values() if r['model'] == m]
        fin = [r for r in rs if r['exit_status'] in FINAL]
        c = Counter(r['exit_status'] for r in rs)
        s = (g.get('models') or {}).get(m, {})
        total = plan_total.get(m) or N_TASKS * N_ARMS * samples[m]
        costs = [r.get('cost_usd') or 0 for r in fin]
        mean = statistics.mean(costs) if costs else 0
        p90 = sorted(costs)[int(0.9 * (len(costs) - 1))] if costs else 0
        sp = s.get('spend_usd', 0)
        proj = sp + mean * max(total - len(fin), 0) if costs else sp
        proj_total += proj
        st = s.get('state', 'closed'); br = st if st == 'closed' else f"{st}[{s.get('kind')}: {s.get('reason')}]"
        print(f"{m:<16} {len(fin):>4}/{total:<4} {c['Submitted']:>4} {c['LimitsExceeded']:>3} {c['Refusal']:>3} "
              f"{sum(v for k, v in c.items() if k not in FINAL):>4} {sum(1 for r in fin if r.get('oracle_rc') == 0):>4} "
              f"{sp:>7.2f} {s.get('cap_usd', 0):>4.0f} {mean:>6.3f} {p90:>6.3f} {proj:>7.2f} "
              f"{statistics.median([r.get('n_commands') or 0 for r in fin]) if fin else 0:>6} "
              f"{statistics.median([r.get('duration') or 0 for r in fin]) if fin else 0:>6.0f} {s.get('active_runs', 0):>3}  {br}")
    print(f"projected total at current mean $/run: ${proj_total:.2f}")
    fails = [r for r in latest.values() if r['exit_status'] not in FINAL]
    if fails:
        print('non-final runs (retried once on next launch):')
        for r in fails[-6:]: print(f"  {r['run_id']} {r['model']} {r['exit_status']} attempt={r.get('attempt')} {(r.get('error') or r.get('note') or '')[:120]}")
    if cont:
        print('active containers: ' + '; '.join(x.replace('forkdpo-e2e-', '').replace('\t', ' ') for x in cont[:20]))
    lf = ROOT / 'logs/e2e.log'
    if lf.exists() and a.log:
        print('-- log tail --')
        for l in lf.read_text().splitlines()[-a.log:]: print('  ' + l[:220])


if __name__ == '__main__':
    main()
