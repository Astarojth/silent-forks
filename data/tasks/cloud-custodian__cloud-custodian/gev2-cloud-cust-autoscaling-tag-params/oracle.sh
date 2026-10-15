set -e
grep -qF "zz_extra_entry" "c7n/actions/autoscaling.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/test_eventbridge.py -q 2>&1 | tail -3
