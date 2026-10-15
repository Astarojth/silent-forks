set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/iam/policy_validation.py'); s = p.read_text()
old = '["Version", "Id", "Statement", "Conditions"]'; new = '["Version", "Id", "Statement", "Conditions", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
