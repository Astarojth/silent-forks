#!/bin/bash
set -x
cd /pdm
pip install -q -e . || echo "[INSTALL_STEP_FAILED] 0"
pip install -q -e '.[pytest]' || echo "[INSTALL_STEP_FAILED] 1"
pip install -q -e '.[msgpack]' || echo "[INSTALL_STEP_FAILED] 2"
pip install -q pytest-xdist pytest-cov pytest-httpserver || echo "[INSTALL_STEP_FAILED] 3"
pip install -q 'hishel==0.0.32' || echo "[INSTALL_STEP_FAILED] 4"
pip install -e . 2>/dev/null || pip install -e . --no-build-isolation 2>/dev/null || true || echo "[INSTALL_STEP_FAILED] 5"
for e in all dev test tests testing; do pip install -e ".[$e]" 2>/dev/null || true; done; true || echo "[INSTALL_STEP_FAILED] 6"
for f in requirements-dev.txt requirements_dev.txt dev-requirements.txt requirements/dev.txt requirements/test.txt requirements/tests.txt requirements-test.txt test-requirements.txt tests/requirements.txt; do [ -f $f ] && pip install -r $f || true; done || echo "[INSTALL_STEP_FAILED] 7"
pip install pytest pytest-xdist pytest-socket pytest-timeout pytest-cov pytest-mock pytest-asyncio pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 8"
