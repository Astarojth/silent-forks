apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 >/dev/null 2>&1 && rm -rf /var/lib/apt/lists/* || echo "[INSTALL_STEP_FAILED] python3"
cd /jaeger && (go build ./... >/dev/null 2>&1 || echo "[WARM] go build ./... failed")
