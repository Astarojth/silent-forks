#!/bin/bash
set -x
cd /streamlink
python -m pip install --upgrade pip setuptools wheel || echo "[INSTALL_STEP_FAILED] 0"
pip install versioningit || echo "[INSTALL_STEP_FAILED] 1"
pip install -e . || echo "[INSTALL_STEP_FAILED] 2"
pip install -e '.[dev]' 2>/dev/null || true || echo "[INSTALL_STEP_FAILED] 3"
pip install requests-mock freezegun pytest-trio trio pytest-asyncio || true || echo "[INSTALL_STEP_FAILED] 4"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-timeout pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 5"
