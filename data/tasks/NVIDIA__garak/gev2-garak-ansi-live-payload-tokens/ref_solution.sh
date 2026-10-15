set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('garak/resources/ansi.py'); s = p.read_text()
old = '[\n    "\\x1b[",\n    "\\x1b]",\n    "\\x9b",\n    "\\x9d",\n]'; new = '[\n    "\\x1b[",\n    "\\x1b]",\n    "\\x9b",\n    "\\x9d",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
