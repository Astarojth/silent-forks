set -e
grep -qF "zz_extra_entry" "src/ogx_api/openai_responses.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/integration/agents/test_openai_responses.py -q 2>&1 | tail -2
