set -e
grep -qF "zz_extra_entry" "garak/probes/dra.py" || { echo "entry missing"; exit 1; }
pytest tests/probes/test_probes_dra.py -q 2>&1 | tail -3
