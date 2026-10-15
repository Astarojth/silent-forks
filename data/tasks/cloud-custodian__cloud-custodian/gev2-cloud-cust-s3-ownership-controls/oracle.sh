set -e
grep -qF "zz_extra_entry" "c7n/resources/s3.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/test_s3.py -q 2>&1 | tail -3
