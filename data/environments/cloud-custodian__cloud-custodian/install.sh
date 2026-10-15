#!/bin/bash
set -x
cd /cloud-custodian
python -m pip install --upgrade pip uv || echo "[INSTALL_STEP_FAILED] 0"
timeout 1500 uv sync --all-groups --all-extras || uv sync --all-groups || uv sync || echo "[INSTALL_STEP_FAILED] 1"
uv pip install adal pytest pytest-xdist pytest-mock freezegun placebo vcrpy || true || echo "[INSTALL_STEP_FAILED] 2"
