#!/bin/bash
set -x
cd /litellm
pip install -q -r requirements.txt || echo "[INSTALL_STEP_FAILED] 0"
pip install -q -e . || echo "[INSTALL_STEP_FAILED] 1"
