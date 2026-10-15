#!/bin/bash
set -x
cd /troposphere
pip install -q -r requirements.txt || echo "[INSTALL_STEP_FAILED] 0"
pip install -q -r requirements-dev.txt || echo "[INSTALL_STEP_FAILED] 1"
pip install -q -e . || echo "[INSTALL_STEP_FAILED] 2"
pip install pytest pytest-xdist pytest-socket pytest-timeout pytest-cov pytest-mock pytest-asyncio || true || echo "[INSTALL_STEP_FAILED] 3"
