set -e
grep -qF "zz_extra_entry" "tools/c7n_azure/c7n_azure/resources/cosmos_db.py" || { echo "entry missing"; exit 1; }
uv run pytest tools/c7n_azure/tests_azure/tests_resources/test_cosmos_db.py -q 2>&1 | tail -2
