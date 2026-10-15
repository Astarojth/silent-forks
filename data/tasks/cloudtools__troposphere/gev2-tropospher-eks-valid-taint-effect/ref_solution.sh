set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('troposphere/validators/eks.py'); s = p.read_text()
old = '["NO_EXECUTE", "NO_SCHEDULE", "PREFER_NO_SCHEDULE"]'; new = '["NO_EXECUTE", "NO_SCHEDULE", "PREFER_NO_SCHEDULE", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
