#!/bin/bash
set -x
cd /dynaconf
pip install -e .[test] --quiet || echo "[INSTALL_STEP_FAILED] 0"
pip install -q redis hvac ruamel.yaml toml configobj || echo "[INSTALL_STEP_FAILED] extra"
