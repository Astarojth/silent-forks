set -e
grep -qF "zz_extra_entry" "build_backend/plugins_json.py" || { echo "entry missing"; exit 1; }
pytest build_backend/test_plugins_json.py -q 2>&1 | tail -2
