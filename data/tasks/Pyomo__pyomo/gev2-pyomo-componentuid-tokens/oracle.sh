set -e
grep -qF "zz_extra_entry" "pyomo/core/base/componentuid.py" || { echo "entry missing"; exit 1; }
python -m pytest pyomo/core/tests/unit/test_componentuid.py -q 2>&1 | tail -3
