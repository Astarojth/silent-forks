#!/bin/bash
set -x
cd /haystack
python -m pip install --upgrade pip setuptools wheel || echo "[INSTALL_STEP_FAILED] 0"
pip install -e . || echo "[INSTALL_STEP_FAILED] 1"
pip install pandas pyarrow pillow arrow structlog jsonschema pytest-bdd pytest-asyncio pytest-mock || true || echo "[INSTALL_STEP_FAILED] 2"
pip install -r test/test_requirements.txt 2>/dev/null || true || echo "[INSTALL_STEP_FAILED] 3"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-timeout pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 4"
