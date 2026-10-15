set -e
grep -qF "zz_extra_entry" "certbot/src/certbot/_internal/renewal.py" || { echo "entry missing"; exit 1; }
python -m pytest certbot/src/certbot/_internal/tests/renewal_test.py -q 2>&1 | tail -3
