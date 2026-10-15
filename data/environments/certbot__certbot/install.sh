#!/bin/bash
set -x
cd /certbot
python -m pip install --upgrade pip setuptools wheel || echo "[INSTALL_STEP_FAILED] 0"
pip install -e acme -e certbot || echo "[INSTALL_STEP_FAILED] 1"
pip install configargparse configobj cloudflare pyrfc3339 pytz josepy || true || echo "[INSTALL_STEP_FAILED] 2"
pip install -e certbot-dns-cloudflare -e certbot-nginx 2>/dev/null || true || echo "[INSTALL_STEP_FAILED] 3"
pip install pytest pytest-xdist pytest-asyncio pytest-mock pytest-timeout pytest-httpserver requests-mock responses freezegun hypothesis || true || echo "[INSTALL_STEP_FAILED] 4"
