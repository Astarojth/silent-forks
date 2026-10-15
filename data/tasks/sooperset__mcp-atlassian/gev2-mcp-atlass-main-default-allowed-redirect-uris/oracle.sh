set -e
grep -qF "zz_extra_entry" "src/mcp_atlassian/servers/main.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/servers/test_tool_policy_contract.py -q 2>&1 | tail -3
