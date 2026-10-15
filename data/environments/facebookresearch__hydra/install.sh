#!/bin/bash
set -x
cd /hydra
apt-get update -qq && apt-get install -y -qq default-jre-headless >/dev/null 2>&1 || true || echo "[INSTALL_STEP_FAILED] 0"
python -m pip install --upgrade pip setuptools wheel || echo "[INSTALL_STEP_FAILED] 1"
pip install -e '.[dev]' || pip install -e . || echo "[INSTALL_STEP_FAILED] 2"
pip install 'omegaconf>=2.3' pytest || true || echo "[INSTALL_STEP_FAILED] 3"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-timeout pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 4"
