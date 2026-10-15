# Silent Forks

Code and data for *Over-Defense in Coding Agents Begins at Silent Forks*.

A silent fork is a turn where the next actions differ in how much checking they do, while every one of them leads to the same task outcome. A behavioral checker finds these turns, and ForkDPO trains on them: each pair contrasts a proportionate action with a disproportionate one at the same prefix, on both sides of the required behavior (doing more than the task needs, and skipping a required check).

Model weights are not included. Download the base model and train with the scripts below.

## Repository

```text
sf.py                  command-line entry point (python sf.py lists the commands)
src/checker/           behavioral checker and fork labeling
src/rollout/           local bash agent, task checks, and evaluation
src/pairs/             pair construction from agent runs
src/train/             ForkDPO (LoRA DPO) and adapter merge
src/frontier/          frontier models at fork prefixes and as end-to-end agents
data/tasks/            368 tasks from 34 repositories
data/split.json        train and test split
data/environments/     Docker recipes, one per repository
data/pairs/            a sample of the training pairs
scripts/               model download, serving, training, and image builds
docs/                  checker rules, environments, frontier harness
```

A task directory holds `task.json`, the instructions of both arms (`armA/prompt.md`, `armB/prompt.md`), `oracle.sh`, and, for evaluation, `answer_card.md` and `ref_solution.sh`. The agent reads only the instruction of its arm. The instructions are in Chinese, as given to every model in the experiments, and many model replies are in Chinese as well. The paper shows English translations of both, with commands and system prompts verbatim.

## Setup

```bash
pip install -r requirements.txt
bash scripts/download_model.sh            # Qwen/Qwen3.5-4B -> models/base
bash scripts/serve_model.sh               # vLLM on port 8000
```

## Training

```bash
bash scripts/train.sh                     # data/pairs/pairs.jsonl -> work/forkdpo_out
python sf.py merge --adapter work/forkdpo_out/adapter --out models/forkdpo
```

`scripts/train.sh` sets 2 epochs, learning rate 1e-5, beta 0.1, prompt limit 5000, and response limit 1500; LoRA rank 16 is set in `src/train/train_dpo.py`. The pairs in `data/pairs/` are about half of the training pairs, stratified by kind. To build pairs from your own runs:

```bash
python sf.py extract-pairs --runs work/runs    # over-defense pairs, resampled at each fork
python sf.py counter-pairs --runs work/runs    # skipped-check pairs
python sf.py mix-pairs
```

## Evaluation

```bash
bash scripts/build_image.sh jaegertracing__jaeger      # forkdpo-run:jaegertracing__jaeger
python sf.py check-task data/tasks/jaegertracing__jaeger/<task_id>
python sf.py run data/tasks/jaegertracing__jaeger/<task_id> A
python sf.py run-batch --repos jaegertracing__jaeger --reps 8
python sf.py compare work/runs
python sf.py summary
```

`check-task` confirms that the oracle fails on the untouched tree and passes after the reference solution. Runs are written under `work/runs`.

## Frontier models

Set `FORKDPO_API_BASE` and `FORKDPO_API_KEY` (see `.env.example`), then see [docs/frontier.md](docs/frontier.md).

```bash
python sf.py probe                        # next actions at fork prefixes
python sf.py forks label                  # checker labels of the probe samples
python sf.py verify-images jaegertracing__jaeger
python sf.py e2e --phase pilot
python sf.py judge
```

## License

MIT. The tasks are built from public repositories under their own licenses.
