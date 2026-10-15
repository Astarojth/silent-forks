#!/bin/bash
set -x
cd /datamodel-code-generator
python -m pip install --upgrade pip uv || echo "[INSTALL_STEP_FAILED] 0"
uv sync || true || echo "[INSTALL_STEP_FAILED] 1"
uv pip install -e '.[graphql,http,debug,validation]' || uv pip install -e . || true || echo "[INSTALL_STEP_FAILED] 2"
uv pip install pytest pytest-xdist pytest-mock freezegun graphql-core || true || echo "[INSTALL_STEP_FAILED] 3"
