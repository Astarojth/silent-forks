set -e
grep -qF "zz_extra_entry" "garak/resources/ansi.py" || { echo "entry missing"; exit 1; }
pytest tests/probes/test_probes_ansiescape.py -q 2>&1 | tail -3
