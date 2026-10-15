在 `src/mcp_atlassian/jira/sla.py` 里的 `AVAILABLE_METRICS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/jira/test_sla.py -q` 确认没破坏就行。
