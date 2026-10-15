set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/mcp_atlassian/jira/sla.py'); s = p.read_text()
old = '[\n    "cycle_time",\n    "lead_time",\n    "time_in_status",\n    "due_date_compliance",\n    "resolution_time",\n    "first_response_time",\n]'; new = '[\n    "cycle_time",\n    "lead_time",\n    "time_in_status",\n    "due_date_compliance",\n    "resolution_time",\n    "first_response_time",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
