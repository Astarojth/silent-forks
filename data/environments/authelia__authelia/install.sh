#!/bin/bash
set -x
cd /authelia
export DEBIAN_FRONTEND=noninteractive && apt-get update -qq || echo "[INSTALL_STEP_FAILED] 0"
export DEBIAN_FRONTEND=noninteractive && apt-get install -y -qq wget || echo "[INSTALL_STEP_FAILED] 1"
rm -rf /usr/local/go && export DEBIAN_FRONTEND=noninteractive && cd /tmp && wget https://go.dev/dl/go1.24.4.linux-amd64.tar.gz && tar -C /usr/local -xzf go1.24.4.linux-amd64.tar.gz || echo "[INSTALL_STEP_FAILED] 2"
/usr/local/go/bin/go version || echo "[INSTALL_STEP_FAILED] 3"
ln -sf /usr/local/go/bin/go /usr/local/bin/go || echo "[INSTALL_STEP_FAILED] 4"
export DEBIAN_FRONTEND=noninteractive && export PATH=/usr/local/go/bin:$PATH && cd /authelia && /usr/local/go/bin/go mod tidy || echo "[INSTALL_STEP_FAILED] 5"
apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /authelia && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
