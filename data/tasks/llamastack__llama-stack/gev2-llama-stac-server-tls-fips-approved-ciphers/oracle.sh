set -e
grep -qF "zz_extra_entry" "src/ogx/core/server_tls.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/server/test_tls_config.py -q 2>&1 | tail -3
