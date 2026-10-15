set -e
grep -qF "zz_extra_entry" "c7n/resources/keyspaces.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/test_keyspaces.py -q 2>&1 | tail -2
