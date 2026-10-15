#!/bin/bash
set -x
cd /llama-stack
python -m pip install --upgrade pip uv || echo "[INSTALL_STEP_FAILED] 0"
uv sync --group dev --group unit || uv sync --all-groups || uv sync || echo "[INSTALL_STEP_FAILED] 1"
uv pip install pytest pytest-asyncio pytest-mock pytest-timeout || true || echo "[INSTALL_STEP_FAILED] 2"
