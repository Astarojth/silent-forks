在 `src/mcp_atlassian/models/jira/issue.py` 里的 `EPIC_LINK_PATTERNS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/jira/test_project_analysis.py -q` 确认没破坏就行。
