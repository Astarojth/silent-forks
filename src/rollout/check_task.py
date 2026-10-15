#!/usr/bin/env python3
"""Self-check one task in its image: for each arm, (1) arm setup applies cleanly, (2) oracle FAILS on untouched tree (no-op),
(3) oracle PASSES after ref_solution.sh, (4) optional decoy_solution.sh also passes oracle. Writes work/checks/<task_id>.json.
usage: check_task.py data/tasks/<repo>/<task_id> [--arms AB]"""
import argparse, json, pathlib, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[2]

def dexec(c, cmd, workdir, stdin=None, timeout=1500):
    return subprocess.run(['docker', 'exec', '-i', '-w', workdir, c, 'bash', '-lc', cmd], capture_output=True, text=True, input=stdin, timeout=timeout)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('task_dir'); ap.add_argument('--arms', default='AB'); a = ap.parse_args()
    td = pathlib.Path(a.task_dir).resolve(); task = json.loads((td / 'task.json').read_text())
    image = task.get('image') or 'forkdpo-run:' + task['repo'].replace('/', '__'); wd = task['workdir']
    report = dict(task_id=task['task_id'], checked=time.strftime('%Y-%m-%dT%H:%M:%S'), arms={})
    allok = True
    for arm in a.arms:
        c = f"forkdpo-check-{task['task_id']}-{arm}"[:60]
        subprocess.run(['docker', 'rm', '-f', c], capture_output=True)
        r = subprocess.run(['docker', 'run', '-d', '--platform', 'linux/amd64', '--name', c, image, 'sleep', '3600'], capture_output=True, text=True)
        if r.returncode: print('docker run failed', r.stderr); sys.exit(1)
        res = {}
        try:
            dexec(c, 'git config core.fileMode false && git update-index -q --refresh || true', wd)
            ad = td / f'arm{arm}'
            if (ad / 'overlay').is_dir():
                subprocess.run(['docker', 'cp', str(ad / 'overlay') + '/.', f'{c}:{wd}/'], check=True)
            if (ad / 'setup.sh').exists():
                r = dexec(c, 'bash -s', wd, stdin=(ad / 'setup.sh').read_text()); res['setup_rc'] = r.returncode; res['setup_err'] = r.stderr[-1500:]
            res['git_status_after_setup'] = dexec(c, 'git status --porcelain | head -20', wd).stdout
            res['git_log_top'] = dexec(c, 'git log -3 --format="%h %ad %an %s" --date=short', wd).stdout
            oracle = (td / 'oracle.sh').read_text()
            r = dexec(c, 'bash -s', wd, stdin=oracle); res['noop_rc'] = r.returncode; res['noop_out'] = (r.stdout + r.stderr)[-1500:]
            res['tree_clean_after_oracle'] = dexec(c, 'git status --porcelain', wd).stdout == ''
            r = dexec(c, 'bash -s', wd, stdin=(td / 'ref_solution.sh').read_text()); res['ref_apply_rc'] = r.returncode; res['ref_apply_err'] = r.stderr[-1500:]
            r = dexec(c, 'bash -s', wd, stdin=oracle); res['ref_rc'] = r.returncode; res['ref_out'] = (r.stdout + r.stderr)[-1500:]
            res['ref_diff_stat'] = dexec(c, 'git --no-pager diff --stat', wd).stdout
            if (td / 'decoy_solution.sh').exists():
                dexec(c, 'git checkout -q -- . && git clean -fdq', wd)
                r = dexec(c, 'bash -s', wd, stdin=(td / 'decoy_solution.sh').read_text()); res['decoy_apply_rc'] = r.returncode
                r = dexec(c, 'bash -s', wd, stdin=oracle); res['decoy_rc'] = r.returncode
            res['ok'] = res.get('setup_rc', 0) == 0 and (res['noop_rc'] != 0 or task.get('noop_na')) and res['ref_apply_rc'] == 0 and res['ref_rc'] == 0 and res.get('decoy_rc', 0) == 0
        finally:
            subprocess.run(['docker', 'rm', '-f', c], capture_output=True)
        report['arms'][arm] = res; allok = allok and res['ok']
        print(f"{task['task_id']} arm {arm}: setup={res.get('setup_rc',0)} noop_rc={res['noop_rc']} ref_apply={res['ref_apply_rc']} ref_rc={res['ref_rc']} ok={res['ok']}")
        if not res['ok']: print('   noop_out:', res['noop_out'][-600:]); print('   ref_out:', res['ref_out'][-600:]); print('   ref_err:', res['ref_apply_err'][-400:])
    report['ok'] = allok
    out = ROOT / 'work' / 'checks'; out.mkdir(parents=True, exist_ok=True)
    (out / f"{task['task_id']}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if allok else 1

if __name__ == '__main__':
    raise SystemExit(main())
