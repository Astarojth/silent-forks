set -e
grep -qF "zz_extra_entry" "privacyidea/webui/login.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_api_hide_version.py -q 2>&1 | tail -3
