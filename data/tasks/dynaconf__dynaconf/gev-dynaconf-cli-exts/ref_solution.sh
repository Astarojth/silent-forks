set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('dynaconf/cli.py'); s = p.read_text()
old = '["ini", "toml", "yaml", "json", "py", "env"]'; new = '["ini", "toml", "yaml", "json", "py", "env", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
