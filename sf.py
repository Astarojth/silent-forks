#!/usr/bin/env python3
"""Command-line entry point. usage: python sf.py <command> [args...]; python sf.py <command> --help for its options."""
import runpy
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / 'src'
COMMANDS = {
    'check-task': ('rollout/check_task.py', 'oracle fails before and passes after the reference solution'),
    'run': ('rollout/run_task.py', 'one agent run of a task arm'),
    'run-batch': ('rollout/run_batch.py', 'all task arms, several in parallel'),
    'compare': ('rollout/compare.py', 'violation and disproportion rates of one or more run sets'),
    'summary': ('rollout/summary.py', 'rates per arm, path, and model of a run set'),
    'extract-pairs': ('pairs/extract.py', 'over-defense pairs at silent forks'),
    'counter-pairs': ('pairs/counter.py', 'skipped-check pairs'),
    'mix-pairs': ('pairs/mix.py', 'training mix of both pair kinds'),
    'train': ('train/train_dpo.py', 'LoRA DPO on the pairs'),
    'merge': ('train/merge_lora.py', 'merge the adapter into the base model'),
    'forks': ('checker/forks.py', 'label actions at fork prefixes'),
    'sensitivity': ('checker/sensitivity.py', 'fork labels under each checker mode'),
    'probe': ('frontier/probe.py', 'frontier models at fork prefixes'),
    'probe-status': ('frontier/probe_status.py', 'progress of probe'),
    'verify-images': ('frontier/verify_images.py', 'oracle check of a repository image'),
    'e2e': ('frontier/e2e.py', 'frontier models as agents on the test tasks'),
    'e2e-status': ('frontier/e2e_status.py', 'progress of e2e'),
    'judge': ('frontier/judge.py', 'checker labels of the e2e runs'),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        for name, (_, desc) in COMMANDS.items():
            print(f'  {name:14s} {desc}')
        sys.exit(0 if len(sys.argv) < 2 else 2)
    script = SRC / COMMANDS[sys.argv[1]][0]
    sys.argv = [str(script)] + sys.argv[2:]
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    main()
