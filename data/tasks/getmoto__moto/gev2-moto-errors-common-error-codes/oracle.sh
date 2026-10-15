set -e
grep -qF "zz_extra_entry" "moto/core/errors.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_core/test_errors.py -q 2>&1 | tail -3
