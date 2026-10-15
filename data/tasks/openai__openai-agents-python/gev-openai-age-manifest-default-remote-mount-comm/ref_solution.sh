set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/agents/sandbox/manifest.py'); s = p.read_text()
old = '[\n    "ls",\n    "find",\n    "stat",\n    "cat",\n    "less",\n    "head",\n    "tail",\n    "du",\n    "grep",\n    "rg",\n    "wc",\n    "sort",\n    "cut",\n    "cp",\n    "tee",\n    "echo",\n    "mkdir",\n    "rm",\n]'; new = '[\n    "ls",\n    "find",\n    "stat",\n    "cat",\n    "less",\n    "head",\n    "tail",\n    "du",\n    "grep",\n    "rg",\n    "wc",\n    "sort",\n    "cut",\n    "cp",\n    "tee",\n    "echo",\n    "mkdir",\n    "rm",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
