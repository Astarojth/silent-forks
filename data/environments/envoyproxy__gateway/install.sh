#!/bin/bash
set -x
cd /gateway
export DEBIAN_FRONTEND=noninteractive || echo "[INSTALL_STEP_FAILED] 0"
wget https://go.dev/dl/go1.24.4.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 1"
tar -xzf go1.24.4.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 2"
export PATH=/gateway/go/bin:$PATH || echo "[INSTALL_STEP_FAILED] 3"
export GOPATH=/tmp/go || echo "[INSTALL_STEP_FAILED] 4"
mkdir -p $GOPATH || echo "[INSTALL_STEP_FAILED] 5"
export HOME=/tmp || echo "[INSTALL_STEP_FAILED] 6"
export GOCACHE=/tmp/go/cache || echo "[INSTALL_STEP_FAILED] 7"
mkdir -p $GOCACHE || echo "[INSTALL_STEP_FAILED] 8"
go install sigs.k8s.io/controller-runtime/tools/setup-envtest@latest || echo "[INSTALL_STEP_FAILED] 9"
export PATH=$GOPATH/bin:$PATH || echo "[INSTALL_STEP_FAILED] 10"
setup-envtest use 1.29.5 || echo "[INSTALL_STEP_FAILED] 11"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /gateway && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
