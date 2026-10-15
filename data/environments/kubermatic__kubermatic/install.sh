#!/bin/bash
set -x
cd /kubermatic
export DEBIAN_FRONTEND=noninteractive && apt-get update -qq || echo "[INSTALL_STEP_FAILED] 0"
export DEBIAN_FRONTEND=noninteractive && apt-get install -y -qq golang wget || echo "[INSTALL_STEP_FAILED] 1"
export DEBIAN_FRONTEND=noninteractive && wget https://go.dev/dl/go1.23.6.linux-amd64.tar.gz -q || echo "[INSTALL_STEP_FAILED] 2"
rm -rf /usr/local/go && export DEBIAN_FRONTEND=noninteractive && tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 3"
export DEBIAN_FRONTEND=noninteractive && export PATH=/usr/local/go/bin:$PATH && export GOPATH=$HOME/go && mkdir -p $GOPATH || echo "[INSTALL_STEP_FAILED] 4"
/usr/local/go/bin/go version || echo "[INSTALL_STEP_FAILED] 5"
ln -sf /usr/local/go/bin/go /usr/local/bin/go || echo "[INSTALL_STEP_FAILED] 6"
export DEBIAN_FRONTEND=noninteractive && export PATH=/usr/local/go/bin:$PATH && export GOPATH=$HOME/go && /usr/local/go/bin/go mod download || echo "[INSTALL_STEP_FAILED] 7"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /kubermatic && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
