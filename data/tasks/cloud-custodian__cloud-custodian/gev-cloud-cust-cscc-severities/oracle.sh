set -e
grep -qF "zz_extra_entry" "tools/c7n_gcp/c7n_gcp/actions/cscc.py" || { echo "entry missing"; exit 1; }
uv run pytest tools/c7n_gcp/tests/test_cscc.py -q 2>&1 | tail -2
