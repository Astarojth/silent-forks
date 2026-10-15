set -e
grep -qF "zz_extra_entry" "sdv/_utils.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/unit/evaluation/test__utils.py -q 2>&1 | tail -3
