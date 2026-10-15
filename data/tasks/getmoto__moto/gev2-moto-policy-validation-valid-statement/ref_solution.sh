set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/iam/policy_validation.py'); s = p.read_text()
old = '[\n    "Sid",\n    "Action",\n    "NotAction",\n    "Resource",\n    "NotResource",\n    "Effect",\n    "Principal",\n    "NotPrincipal",\n    "Condition",\n]'; new = '[\n    "Sid",\n    "Action",\n    "NotAction",\n    "Resource",\n    "NotResource",\n    "Effect",\n    "Principal",\n    "NotPrincipal",\n    "Condition",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
