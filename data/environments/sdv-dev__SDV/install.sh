#!/bin/bash
set -x
cd /SDV
python -m pip install --upgrade pip || echo "[INSTALL_STEP_FAILED] 0"
pip install -e . || pip install . || true || echo "[INSTALL_STEP_FAILED] 1"
for e in test tests testing dev all; do pip install -e ".[$e]" 2>/dev/null && break; done; true || echo "[INSTALL_STEP_FAILED] 2"
pip install --group dev 2>/dev/null || true; pip install --group test 2>/dev/null || true || echo "[INSTALL_STEP_FAILED] 3"
for f in requirements-dev.txt requirements_dev.txt dev-requirements.txt requirements/dev.txt requirements/test.txt requirements-test.txt test-requirements.txt tests/requirements.txt; do [ -f $f ] && pip install -r $f || true; done || echo "[INSTALL_STEP_FAILED] 4"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-socket pytest-timeout pytest-cov hypothesis python-dotenv || true || echo "[INSTALL_STEP_FAILED] 5"
