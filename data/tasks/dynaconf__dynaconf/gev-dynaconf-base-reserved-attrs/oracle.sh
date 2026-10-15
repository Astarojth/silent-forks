set -e
grep -qF "zz_extra_entry" "dynaconf/base.py" || { echo "entry missing"; exit 1; }
pytest tests/test_base.py -q 2>&1 | tail -2
