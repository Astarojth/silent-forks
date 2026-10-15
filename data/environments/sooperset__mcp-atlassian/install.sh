#!/bin/bash
set -x
cd /mcp-atlassian
python -m pip install --upgrade pip uv || echo "[INSTALL_STEP_FAILED] 0"
uv sync --all-groups --all-extras || uv sync --all-groups || uv sync || echo "[INSTALL_STEP_FAILED] 1"
uv pip install pytest pytest-xdist pytest-asyncio pytest-mock hypothesis python-dotenv || true || echo "[INSTALL_STEP_FAILED] 2"
