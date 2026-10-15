set -e
grep -qF "zz_extra_entry" "src/ogx/cli/stack/_list_deps.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/distribution/test_list_deps_output.py -q 2>&1 | tail -3
