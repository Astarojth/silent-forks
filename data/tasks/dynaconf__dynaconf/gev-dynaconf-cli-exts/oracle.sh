set -e
grep -qF "zz_extra_entry" "dynaconf/cli.py" || { echo "entry missing"; exit 1; }
pytest tests/test_cli.py -q 2>&1 | tail -2
