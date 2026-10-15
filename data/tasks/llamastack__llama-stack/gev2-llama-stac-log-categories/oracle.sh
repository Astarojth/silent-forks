set -e
grep -qF "zz_extra_entry" "src/ogx/log.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/core/test_logging_config.py -q 2>&1 | tail -3
