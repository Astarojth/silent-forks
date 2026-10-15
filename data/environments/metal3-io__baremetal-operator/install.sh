#!/bin/bash
set -x
cd /baremetal-operator
export DEBIAN_FRONTEND=noninteractive || echo "[INSTALL_STEP_FAILED] 0"
apt update || echo "[INSTALL_STEP_FAILED] 1"
apt install -y wget || echo "[INSTALL_STEP_FAILED] 2"
wget https://go.dev/dl/go1.23.7.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 3"
tar -C /usr/local -xzf go1.23.7.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 4"
export PATH=$PATH:/usr/local/go/bin || echo "[INSTALL_STEP_FAILED] 5"
export GOPATH=$HOME/go || echo "[INSTALL_STEP_FAILED] 6"
mkdir -p $GOPATH || echo "[INSTALL_STEP_FAILED] 7"
export GOCACHE=$HOME/.cache/go-build || echo "[INSTALL_STEP_FAILED] 8"
mkdir -p $GOCACHE || echo "[INSTALL_STEP_FAILED] 9"
export GOLANGCI_LINT_CACHE=$HOME/.cache/golangci-lint || echo "[INSTALL_STEP_FAILED] 10"
mkdir -p $GOLANGCI_LINT_CACHE || echo "[INSTALL_STEP_FAILED] 11"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /baremetal-operator && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
