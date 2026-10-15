set -e
grep -qF "zz_extra_entry" "sdv/multi_table/dayz.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/unit/multi_table/test_dayz.py -q 2>&1 | tail -3
