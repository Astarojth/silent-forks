set -e
grep -qF "zz_extra_entry" "smart_open/utils.py" || { echo "entry missing"; exit 1; }
pytest tests/test_utils.py -q 2>&1 | tail -2
