#!/bin/bash
set -x
cd /restic
wget -q https://go.dev/dl/go1.23.0.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 0"
tar -C /usr/local -xzf go1.23.0.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 1"
export PATH=/usr/local/go/bin:$PATH || echo "[INSTALL_STEP_FAILED] 2"
export HOME=/root || echo "[INSTALL_STEP_FAILED] 3"
export GOCACHE=/tmp/gocache || echo "[INSTALL_STEP_FAILED] 4"
mkdir -p $GOCACHE || echo "[INSTALL_STEP_FAILED] 5"
go run build.go || echo "[INSTALL_STEP_FAILED] 6"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /restic && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
