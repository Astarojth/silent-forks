#!/usr/bin/env bash
# Download the base model into models/base.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_ID="${FORKDPO_MODEL_ID:-Qwen/Qwen3.5-4B}"
DEST="${1:-$ROOT/models/base}"
mkdir -p "$DEST"
exec huggingface-cli download "$MODEL_ID" --local-dir "$DEST"
