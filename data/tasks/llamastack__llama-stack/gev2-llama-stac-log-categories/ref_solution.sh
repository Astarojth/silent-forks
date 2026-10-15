set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/log.py'); s = p.read_text()
old = '[\n    "core",\n    "server",\n    "router",\n    "inference",\n    "agents",\n    "tools",\n    "client",\n    "openai",\n    "openai_responses",\n    "openai_conversations",\n    "testing",\n    "providers",\n    "models",\n    "files",\n    "file_processors",\n    "vector_io",\n    "tool_runtime",\n    "cli",\n    "tests",\n    "telemetry",\n    "connectors",\n    "messages",\n    "interactions",\n]'; new = '[\n    "core",\n    "server",\n    "router",\n    "inference",\n    "agents",\n    "tools",\n    "client",\n    "openai",\n    "openai_responses",\n    "openai_conversations",\n    "testing",\n    "providers",\n    "models",\n    "files",\n    "file_processors",\n    "vector_io",\n    "tool_runtime",\n    "cli",\n    "tests",\n    "telemetry",\n    "connectors",\n    "messages",\n    "interactions",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
