#!/bin/bash
set -x
cd /moto
make init || echo "[INSTALL_STEP_FAILED] 0"
