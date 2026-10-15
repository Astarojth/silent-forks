set -e
grep -qF "zz_extra_entry" "src/ogx/core/build.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/cli/test_stack_list_deps.py -q 2>&1 | tail -3
