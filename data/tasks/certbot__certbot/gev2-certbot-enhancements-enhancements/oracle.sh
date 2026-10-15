set -e
grep -qF "zz_extra_entry" "certbot/src/certbot/plugins/enhancements.py" || { echo "entry missing"; exit 1; }
python -m pytest certbot/src/certbot/_internal/tests/plugins/enhancements_test.py -q 2>&1 | tail -3
