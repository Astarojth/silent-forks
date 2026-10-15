set -e
grep -qF "zz_extra_entry" "privacyidea/lib/caconnectors/msca.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_lib_caconnector.py -q 2>&1 | tail -3
