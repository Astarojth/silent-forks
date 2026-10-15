#!/bin/bash
set -x
cd /feast
python -m pip install --upgrade pip uv || echo "[INSTALL_STEP_FAILED] 0"
uv pip install --system -r sdk/python/requirements/py3.11-ci-requirements.txt || uv pip install --system -r sdk/python/requirements/py3.11-requirements.txt || echo "[INSTALL_STEP_FAILED] 1"
uv pip install --system -e sdk/python || pip install -e sdk/python || echo "[INSTALL_STEP_FAILED] 2"
pip install pytest pytest-xdist pytest-timeout pytest-mock || true || echo "[INSTALL_STEP_FAILED] 3"
