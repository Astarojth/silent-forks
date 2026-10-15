set -e
grep -qF "zz_extra_entry" "privacyidea/api/lib/utils.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_lib_logging.py -q 2>&1 | tail -3
