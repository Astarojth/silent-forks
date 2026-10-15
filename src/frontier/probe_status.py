#!/usr/bin/env python3
"""Offline progress report for probe.py: reads results/, breakers.json and STATUS only (no network calls)."""
import json, subprocess, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probe as rp

RECENT_SEC = 15 * 60


def epoch(ts):
    try: return time.mktime(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))
    except Exception: return None


def pids(pattern):
    try: return subprocess.run(['pgrep', '-f', pattern], capture_output=True, text=True).stdout.split()
    except Exception: return []


def main():
    probe = rp.read_records(rp.RES / 'fork_probe.jsonl')
    saved = json.loads(rp.BREAKERS.read_text()) if rp.BREAKERS.exists() else {}
    totals = saved.get('totals')
    if not totals:
        n_pairs = sum(1 for _ in open(rp.PAIRS))
        totals = rp.job_totals(n_pairs)
    summ = rp.model_summary(probe, saved, totals)

    t_now = time.time(); recent = Counter(); last_ts = ''
    for r in probe:
        ts = r.get('ts') or ''; last_ts = max(last_ts, ts); e = epoch(ts)
        if e is not None and t_now - e <= RECENT_SEC: recent[r.get('model')] += 1

    print(f"{'model':<16} {'done/total':>11} {'ok':>5} {'refus':>5} {'err':>4} {'spend':>8} {'cap':>5} "
          f"{'projected':>9} {'last15m':>7}  breaker")
    for m in rp.MODELS:
        s = summ[m]
        print(f"{m:<16} {s['done']:>5}/{s['total']:<5} {s['ok']:>5} {s['refusals']:>5} {s['errors']:>4} "
              f"${s['spend']:>7.2f} ${s['cap']:>4.0f} ${s['projected']:>8.2f} {recent[m]:>7}  {s['breaker']}")

    base = float(saved.get('unrecorded_base_usd', rp.UNRECORDED_USD))
    spent = sum(s['spend'] for s in summ.values()) + base
    projected = sum(s['projected'] for s in summ.values()) + base
    done = sum(s['done'] for s in summ.values()); total = sum(s['total'] for s in summ.values())
    age = t_now - epoch(last_ts) if epoch(last_ts) else None
    print()
    print(f"overall: done {done}/{total} requests; spend ${spent:.2f} of stop-at ${rp.STOP_AT_USD:.0f} / cap ${rp.CAP_USD:.0f} "
          f"(incl. ${base:.2f} flat + ${sum(s['unrecorded'] for s in summ.values()):.2f} per-model unrecorded allowances)")
    print(f"projected total spend: ${projected:.2f}")
    print(f"requests in last 15 min: {sum(recent.values())}")
    print(f"last record: {last_ts or '-'}" + (f" ({age / 60:.1f} min ago)" if age is not None else ''))
    if saved:
        print(f"breakers.json updated {saved.get('updated')}: in-flight reserve ${saved.get('inflight_usd', 0):.2f} "
              f"({sum((saved.get('models') or {}).get(m, {}).get('inflight', 0) for m in rp.MODELS)} requests), "
              f"stop_reason={saved.get('stop_reason')}")
    status = rp.ROOT / 'STATUS'
    if status.exists(): print(f"STATUS: {status.read_text().splitlines()[0]}")
    run = pids('probe.py')
    print(f"processes: probe {','.join(run) or 'not running'}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"status.py error: {type(e).__name__}: {e}")
    sys.exit(0)
