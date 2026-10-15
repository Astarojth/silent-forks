#!/bin/bash
set -x
cd /pyomo
pip install -q -e . || echo "[INSTALL_STEP_FAILED] 0"
pip install -q pytest coverage parameterized pybind11 pytest-parallel || echo "[INSTALL_STEP_FAILED] 1"
pip install pytest pytest-xdist pytest-socket pytest-timeout pytest-cov pytest-mock pytest-asyncio || true || echo "[INSTALL_STEP_FAILED] 2"
