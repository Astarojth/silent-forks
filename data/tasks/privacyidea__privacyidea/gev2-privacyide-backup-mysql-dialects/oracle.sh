set -e
grep -qF "zz_extra_entry" "privacyidea/cli/pimanage/backup.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/cli/test_cli_pimanage.py -q 2>&1 | tail -3
