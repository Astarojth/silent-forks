#!/bin/bash
set -x
cd /cluster-api-provider-hetzner
export DEBIAN_FRONTEND=noninteractive || echo "[INSTALL_STEP_FAILED] 0"
apt-get update -qq || echo "[INSTALL_STEP_FAILED] 1"
apt-get remove -y golang || echo "[INSTALL_STEP_FAILED] 2"
apt-get install -y -qq wget || echo "[INSTALL_STEP_FAILED] 3"
wget -q https://go.dev/dl/go1.23.7.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 4"
tar -C /usr/local -xzf go1.23.7.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 5"
rm go1.23.7.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 6"
export PATH=/usr/local/go/bin:$PATH || echo "[INSTALL_STEP_FAILED] 7"
export HOME=/root || echo "[INSTALL_STEP_FAILED] 8"
export XDG_CACHE_HOME=/root/.cache || echo "[INSTALL_STEP_FAILED] 9"
mkdir -p $HOME $XDG_CACHE_HOME || echo "[INSTALL_STEP_FAILED] 10"
make setup-envtest || echo "[INSTALL_STEP_FAILED] 11"
make gotestsum || echo "[INSTALL_STEP_FAILED] 12"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /cluster-api-provider-hetzner && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
