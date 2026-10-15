set -e
grep -qF "zz_extra_entry" "src/ogx/providers/registry/inference.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/cli/test_stack_utils.py -q 2>&1 | tail -3
