set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/mcp_atlassian/models/jira/issue.py'); s = p.read_text()
old = '[\n    r"epic\\s*name",\n    r"epic[._-]?name",\n    r"epicname",\n]'; new = '[\n    r"epic\\s*name",\n    r"epic[._-]?name",\n    r"epicname",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
