#!/usr/bin/env bash
# Serve a local model with vLLM.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL="${FORKDPO_MODEL:-$ROOT/models/base}"
PORT="${PORT:-8000}"
NAME="${SERVED_NAME:-Qwen3.5-4B}"
exec vllm serve "$MODEL" \
  --served-model-name "$NAME" \
  --port "$PORT" \
  --max-model-len 131072 \
  --gpu-memory-utilization 0.85 \
  --enable-prefix-caching \
  --reasoning-parser qwen3 \
  --limit-mm-per-prompt '{"image":0,"video":0}'
