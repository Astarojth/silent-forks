set -e
grep -qF "zz_extra_entry" "src/streamlink_cli/constants.py" || { echo "entry missing"; exit 1; }
pytest tests/cli/main/test_output_stream.py -q 2>&1 | tail -3
