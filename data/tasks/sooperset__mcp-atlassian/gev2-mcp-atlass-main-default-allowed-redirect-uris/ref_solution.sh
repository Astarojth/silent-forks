set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/mcp_atlassian/servers/main.py'); s = p.read_text()
old = '[\n    "http://localhost:*",\n    "http://127.0.0.1:*",\n    "https://chatgpt.com/connector_platform_oauth_redirect",\n    "https://chat.openai.com/connector_platform_oauth_redirect",\n]'; new = '[\n    "http://localhost:*",\n    "http://127.0.0.1:*",\n    "https://chatgpt.com/connector_platform_oauth_redirect",\n    "https://chat.openai.com/connector_platform_oauth_redirect",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
