set -e
grep -qF "zz_extra_entry" "garak/probes/packagehallucination.py" || { echo "entry missing"; exit 1; }
pytest tests/probes/test_probes_packagehallucination.py -q 2>&1 | tail -3
