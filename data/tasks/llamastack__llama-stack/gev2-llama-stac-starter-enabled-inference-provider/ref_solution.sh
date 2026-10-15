set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/distributions/starter/starter.py'); s = p.read_text()
old = '[\n    "ollama",\n    "vllm",\n    "fireworks",\n    "together",\n    "gemini",\n    "vertexai",\n    "groq",\n    "sambanova",\n    "anthropic",\n    "openai",\n    "cerebras",\n    "nvidia",\n    "bedrock",\n    "azure",\n    "meta",\n]'; new = '[\n    "ollama",\n    "vllm",\n    "fireworks",\n    "together",\n    "gemini",\n    "vertexai",\n    "groq",\n    "sambanova",\n    "anthropic",\n    "openai",\n    "cerebras",\n    "nvidia",\n    "bedrock",\n    "azure",\n    "meta",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
