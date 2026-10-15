set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/apigateway/models.py'); s = p.read_text()
old = '["add", "remove", "replace", "move", "copy", "test"]'; new = '["add", "remove", "replace", "move", "copy", "test", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
