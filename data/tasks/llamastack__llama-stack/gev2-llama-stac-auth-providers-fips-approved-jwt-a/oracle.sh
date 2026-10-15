set -e
grep -qF "zz_extra_entry" "src/ogx/core/server/auth_providers.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/server/test_auth_http_client.py -q 2>&1 | tail -3
