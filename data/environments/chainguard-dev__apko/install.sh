#!/bin/bash
set -x
cd /apko
export DEBIAN_FRONTEND=noninteractive || echo "[INSTALL_STEP_FAILED] 0"
apt-get update -qq || echo "[INSTALL_STEP_FAILED] 1"
apt-get install -y -qq wget || echo "[INSTALL_STEP_FAILED] 2"
wget https://go.dev/dl/go1.23.4.linux-amd64.tar.gz -O go.tar.gz || echo "[INSTALL_STEP_FAILED] 3"
rm -rf /usr/local/go && tar -C /usr/local -xzf go.tar.gz || echo "[INSTALL_STEP_FAILED] 4"
export PATH=/usr/local/go/bin:$PATH || echo "[INSTALL_STEP_FAILED] 5"
export GOPATH=$HOME/go || echo "[INSTALL_STEP_FAILED] 6"
export GOCACHE=$HOME/.cache/go-build || echo "[INSTALL_STEP_FAILED] 7"
export XDG_CACHE_HOME=$HOME/.cache || echo "[INSTALL_STEP_FAILED] 8"
mkdir -p $GOCACHE || echo "[INSTALL_STEP_FAILED] 9"
go mod download || echo "[INSTALL_STEP_FAILED] 10"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /apko && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
