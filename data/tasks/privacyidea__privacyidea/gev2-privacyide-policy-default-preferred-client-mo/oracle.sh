set -e
grep -qF "zz_extra_entry" "privacyidea/lib/policy.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_api_offline_no_token.py -q 2>&1 | tail -3
