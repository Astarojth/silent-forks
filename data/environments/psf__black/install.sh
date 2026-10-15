#!/bin/bash
set -x
cd /black
python -m pip install --upgrade pip setuptools wheel || echo "[INSTALL_STEP_FAILED] 0"
pip install -e '.[d,jupyter]' || pip install -e . || echo "[INSTALL_STEP_FAILED] 1"
pip install aiohttp aiohttp-cors || true || echo "[INSTALL_STEP_FAILED] 2"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-timeout pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 3"
