set -e
grep -qF "zz_extra_entry" "sdv/single_table/utils.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/unit/data_processing/test_utils.py -q 2>&1 | tail -3
