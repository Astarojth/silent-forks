# Example preference pairs

These files are a stratified sample of the pairs used to train ForkDPO, about half of each pair kind (seed 17). They are examples for the pair format and for a smaller training run. `python sf.py extract-pairs`, `counter-pairs`, and `mix-pairs` rebuild pairs from agent runs. The user turns are in Chinese, as in the task instructions.

| kind | full | released |
|---|---:|---:|
| `counter-P1` | 135 | 68 |
| `counter-P4` | 55 | 28 |
| `overguard-A-extra-check` | 1 | 1 |
| `overguard-A-off-target-test` | 1 | 1 |
| `overguard-A-subset-recheck` | 2 | 1 |
| `overguard-A-target-repeat` | 131 | 66 |
| `overguard-B-target-repeat` | 46 | 23 |
| `overguard-B-whole-suite` | 136 | 68 |

Released total: 256 of 507.
`pairs.jsonl` is the mix. `over_defense.jsonl` and `skipped_check.jsonl` split it into the two sides of the required behavior.
