#!/bin/bash
set -x
cd /convoy
export PATH=/usr/local/go/bin:$PATH || echo "[INSTALL_STEP_FAILED] 0"
export GOPATH=$HOME/go || echo "[INSTALL_STEP_FAILED] 1"
export GOMODCACHE=$GOPATH/pkg/mod || echo "[INSTALL_STEP_FAILED] 2"
export GOCACHE=$HOME/.cache/go-build || echo "[INSTALL_STEP_FAILED] 3"
export HOME=/root || echo "[INSTALL_STEP_FAILED] 4"
mkdir -p $GOPATH $GOCACHE || echo "[INSTALL_STEP_FAILED] 5"
go mod download || echo "[INSTALL_STEP_FAILED] 6"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /convoy && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed (cache partially warmed)")
