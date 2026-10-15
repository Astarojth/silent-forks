set -e
grep -qF "zz_extra_entry" "src/agents/sandbox/manifest.py" || { echo "entry missing"; exit 1; }
pytest tests/sandbox/test_manifest.py -q 2>&1 | tail -2
