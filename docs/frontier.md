# Frontier models

Both harnesses read `FORKDPO_API_BASE` and `FORKDPO_API_KEY`, and the models are listed at the top of each script.

## Fork prefixes

`python sf.py probe` sends each silent-fork prefix in `data/pairs/pairs.jsonl` to the models and records their next actions; `python sf.py probe-status` reports progress. Outputs go under `work/probe`.

`python sf.py forks validate` labels the 4B model's chosen and rejected actions at every fork, `python sf.py forks label` labels the probe samples, and `python sf.py sensitivity` compares the two checker modes.

## End-to-end runs

`python sf.py e2e` runs the models as agents on the test tasks, one bash tool call at a time, inside `forkdpo-run:<owner__repo>` containers. A repository's tasks start only after `python sf.py verify-images <owner__repo>` has checked its image. `python sf.py judge` labels the finished runs with `src/checker/checker.py`, and `python sf.py e2e-status` reports progress. Runs, request logs, and status files go under `work/e2e`.
