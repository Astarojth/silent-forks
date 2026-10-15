#!/bin/bash
set -x
cd /privacyidea
python -m pip install --upgrade pip setuptools wheel || echo "[INSTALL_STEP_FAILED] 0"
pip install -e . || pip install -r requirements.txt || echo "[INSTALL_STEP_FAILED] 1"
pip install -r tests/requirements.txt 2>/dev/null || pip install -r requirements-dev.txt 2>/dev/null || true || echo "[INSTALL_STEP_FAILED] 2"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-timeout pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 3"
