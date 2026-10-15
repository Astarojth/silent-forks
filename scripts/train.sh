#!/usr/bin/env bash
# Train a ForkDPO LoRA adapter on the released pairs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export FORKDPO_MODEL="${FORKDPO_MODEL:-$ROOT/models/base}"
exec python src/train/train_dpo.py \
  --pairs "${PAIRS:-data/pairs/pairs.jsonl}" \
  --out "${OUT:-work/forkdpo_out}" \
  --model "$FORKDPO_MODEL" \
  --epochs 2 \
  --lr 1e-5 \
  --beta 0.1 \
  --max-prompt-tok 5000 \
  --max-completion-tok 1500
