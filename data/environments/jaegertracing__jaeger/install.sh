#!/bin/bash
set -x
cd /jaeger
wget -q https://go.dev/dl/go1.24.4.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 0"
rm -rf /usr/local/go && tar -C /usr/local -xzf go1.24.4.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 1"
export PATH=/usr/local/go/bin:$PATH && export GOPATH=/go && export GOCACHE=/tmp/go-cache && export GOMODCACHE=/go/pkg/mod && mkdir -p $GOCACHE $GOMODCACHE || echo "[INSTALL_STEP_FAILED] 2"
export PATH=/usr/local/go/bin:$PATH && export GOPATH=/go && export GOCACHE=/tmp/go-cache && export GOMODCACHE=/go/pkg/mod && git submodule update --init --recursive || echo "[INSTALL_STEP_FAILED] 3"
/usr/local/go/bin/go version || echo "[INSTALL_STEP_FAILED] 4"
ln -sf /usr/local/go/bin/go /usr/local/bin/go || echo "[INSTALL_STEP_FAILED] 5"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /jaeger && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
