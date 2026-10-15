set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/core/utils.py'); s = p.read_text()
old = '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]'; new = '["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
