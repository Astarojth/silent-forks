set -e
grep -qF "zz_extra_entry" "src/ogx/core/storage/sqlstore/sqlstore.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/utils/sqlstore/test_sqlstore.py -q 2>&1 | tail -3
