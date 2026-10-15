#!/usr/bin/env python3
"""Run every (task, arm) with run_task.py, N in parallel, alternating vLLM ports. Resume-safe: skips (task, arm)
pairs that already have `--reps` runs in <runs_root>. Only tasks whose image exists are scheduled.
usage: run_batch.py [--workers 6] [--ports 8000] [--reps 1] [--repos a,b] [--tasks id1,id2] [--runs-root work/runs]"""
import argparse, json, pathlib, subprocess, sys, concurrent.futures as cf, time, itertools, threading
ROOT = pathlib.Path(__file__).resolve().parents[2]
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6); ap.add_argument('--ports', default='8000'); ap.add_argument('--reps', type=int, default=1)
    ap.add_argument('--repos', default=''); ap.add_argument('--tasks', default=''); ap.add_argument('--runs-root', default='work/runs'); ap.add_argument('--extra', default=''); ap.add_argument('--tasks-glob', default='data/tasks/*/*/task.json'); ap.add_argument('--arms', default='AB')
    a = ap.parse_args()
    ports = [int(p) for p in a.ports.split(',')]
    images = set(subprocess.run(['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}'], capture_output=True, text=True).stdout.split())
    jobs = []
    for tj in sorted(ROOT.glob(a.tasks_glob)):
        t = json.loads(tj.read_text()); key = t['repo'].replace('/', '__')
        if a.repos and key not in a.repos.split(',') and t['repo'] not in a.repos.split(','): continue
        if a.tasks and t['task_id'] not in a.tasks.split(','): continue
        if (t.get('image') or f'forkdpo-run:{key}') not in images: continue
        for arm in a.arms:
            done = sum(1 for p in (ROOT / a.runs_root / key / t['task_id'] / arm).glob('*/config.json'))
            for _ in range(max(0, a.reps - done)): jobs.append((str(tj.parent), arm))
    print(f'{len(jobs)} runs to do', flush=True)
    counter = itertools.count(); lock = threading.Lock()
    def work(job):
        task_dir, arm = job
        with lock: i = next(counter)
        port = ports[i % len(ports)]
        cmd = [sys.executable, str(ROOT / 'src' / 'rollout' / 'run_task.py'), task_dir, arm, '--port', str(port), '--runs-root', a.runs_root] + (a.extra.split() if a.extra else [])
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3000 * 2 + 3600)
        line = (r.stdout.strip().splitlines() or [''])[-1]
        return f"[{time.strftime('%H:%M:%S')}] {pathlib.Path(task_dir).name} {arm} port={port} rc={r.returncode} {round(time.time()-t0)}s | {line} {('ERR: ' + r.stderr.strip().splitlines()[-1][:300]) if r.returncode else ''}"
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for line in ex.map(work, jobs): print(line, flush=True)
if __name__ == '__main__': main()
