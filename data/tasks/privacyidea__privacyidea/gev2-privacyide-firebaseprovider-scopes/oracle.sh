set -e
grep -qF "zz_extra_entry" "privacyidea/lib/smsprovider/FirebaseProvider.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_api_ttype.py -q 2>&1 | tail -3
