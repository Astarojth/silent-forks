set -e
grep -qF "zz_extra_entry" "src/mcp_atlassian/models/jira/issue.py" || { echo "entry missing"; exit 1; }
uv run pytest tests/unit/jira/test_project_analysis.py -q 2>&1 | tail -3
