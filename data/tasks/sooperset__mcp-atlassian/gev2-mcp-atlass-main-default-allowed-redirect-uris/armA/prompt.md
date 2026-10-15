在 `src/mcp_atlassian/servers/main.py` 里的 `DEFAULT_ALLOWED_REDIRECT_URIS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/servers/test_tool_policy_contract.py -q` 确认没破坏就行。
