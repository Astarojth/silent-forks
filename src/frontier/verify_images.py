#!/usr/bin/env python3
"""Verify forkdpo-run images: for P4 tasks the oracle must fail on the untouched tree and pass after ref_solution.sh;
for P1 tasks (oracle = clean tree, no-op passes by design) the target command must produce test results and the
oracle must pass. Writes env/<repo_key>/VERIFIED (or FAILED) under the e2e root, which e2e.py waits for.
usage: verify_images.py <repo_key> [n_tasks_per_path]"""
import json, os, sys, subprocess, importlib.util as u
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
ROOT = Path(os.environ.get('FORKDPO_E2E_ROOT', REPO / 'work' / 'e2e'))
s = u.spec_from_file_location('cg', REPO / 'src/checker/checker.py'); cg = u.module_from_spec(s); s.loader.exec_module(cg)


def dexec(c, cmd, wd, stdin=None, timeout=1500):
    try:
        return subprocess.run(['docker', 'exec', '-i', '-w', wd, c, 'bash', '-lc', cmd], capture_output=True, text=True,
                              errors='replace', input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, -1, '', 'TIMEOUT')


def verify(tdir):
    t = json.loads((tdir / 'task.json').read_text()); key = t['repo'].replace('/', '__'); wd = t['workdir']; g = t['gen']
    c = f"forkdpo-e2e-verify-{t['task_id']}"[:100]
    subprocess.run(['docker', 'rm', '-f', c], capture_output=True)
    subprocess.run(['docker', 'run', '-d', '--name', c, '--memory', '3g', '--cpus', '3', f'forkdpo-run:{key}', 'sleep', '7200'], check=True, capture_output=True)
    out = dict(task=t['task_id'], path=g['path'])
    try:
        head = dexec(c, 'git rev-parse --short HEAD; git status --porcelain | head -5', wd).stdout.split('\n')
        out['head'] = head[0]; out['dirty'] = [x for x in head[1:] if x]
        oracle = (tdir / 'oracle.sh').read_text()
        if g['path'] == 'P4':
            r0 = dexec(c, 'bash -s', wd, oracle); out['noop_oracle_rc'] = r0.returncode
            r1 = dexec(c, 'bash -s', wd, (tdir / 'ref_solution.sh').read_text()); out['ref_rc'] = r1.returncode
            r2 = dexec(c, 'bash -s', wd, oracle); out['ref_oracle_rc'] = r2.returncode; out['ref_oracle_tail'] = (r2.stdout + r2.stderr)[-300:]
            out['ok'] = r0.returncode != 0 and r1.returncode == 0 and r2.returncode == 0
        else:
            r = dexec(c, g['target_cmd'] + ' 2>&1', wd)
            eff = cg.effective(dict(output=r.stdout + r.stderr))
            out['target_rc'] = r.returncode; out['target_effective'] = eff; out['target_tail'] = (r.stdout + r.stderr)[-300:]
            r2 = dexec(c, 'bash -s', wd, oracle); out['oracle_rc'] = r2.returncode
            out['ok'] = eff and r2.returncode == 0
    finally:
        subprocess.run(['docker', 'rm', '-f', c], capture_output=True)
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__); sys.exit(0)
    key = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    split = json.loads((REPO / 'data' / 'split.json').read_text())['eval']
    by = {}
    for tid in split:
        d = REPO / 'data' / 'tasks' / key / tid
        if d.exists():
            p = json.loads((d / 'task.json').read_text())['gen']['path']
            if p in ('P1', 'P4'): by.setdefault(p, []).append(d)
    ok = True
    for p, ds in sorted(by.items()):
        for d in ds[:n]:
            r = verify(d); ok = ok and r['ok']
            print(json.dumps(r, ensure_ascii=False), flush=True)
    mark = ROOT / 'env' / key; mark.mkdir(parents=True, exist_ok=True)
    for f in ('VERIFIED', 'FAILED'): (mark / f).unlink(missing_ok=True)
    (mark / ('VERIFIED' if ok and by else 'FAILED')).touch()


if __name__ == '__main__':
    main()
