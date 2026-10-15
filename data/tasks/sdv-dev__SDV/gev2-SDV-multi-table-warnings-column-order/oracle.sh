set -e
grep -qF "zz_extra_entry" "sdv/metadata/multi_table.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/unit/evaluation/test_multi_table.py -q 2>&1 | tail -3
