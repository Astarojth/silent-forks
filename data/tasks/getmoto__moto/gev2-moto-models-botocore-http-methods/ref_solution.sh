set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/core/models.py'); s = p.read_text()
old = '["GET", "DELETE", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]'; new = '["GET", "DELETE", "HEAD", "OPTIONS", "PATCH", "POST", "PUT", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
