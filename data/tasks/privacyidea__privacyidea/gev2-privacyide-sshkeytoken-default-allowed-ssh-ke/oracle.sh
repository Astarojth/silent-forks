set -e
grep -qF "zz_extra_entry" "privacyidea/lib/tokens/sshkeytoken.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_migration_b8c9d0e1f2a3.py -q 2>&1 | tail -3
