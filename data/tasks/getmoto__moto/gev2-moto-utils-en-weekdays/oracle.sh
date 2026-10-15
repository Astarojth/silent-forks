set -e
grep -qF "zz_extra_entry" "moto/core/utils.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_swf/test_utils.py -q 2>&1 | tail -3
