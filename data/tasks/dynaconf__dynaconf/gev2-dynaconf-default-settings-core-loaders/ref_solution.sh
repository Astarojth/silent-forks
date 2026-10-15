set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('dynaconf/default_settings.py'); s = p.read_text()
old = '["YAML", "TOML", "INI", "JSON", "PY"]'; new = '["YAML", "TOML", "INI", "JSON", "PY", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
