set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/core/errors.py'); s = p.read_text()
old = '[\n    "InvalidParameterCombination",\n    "InvalidParameterException",\n    "InvalidParameterValue",\n    "ValidationError",\n    "ValidationException",\n]'; new = '[\n    "InvalidParameterCombination",\n    "InvalidParameterException",\n    "InvalidParameterValue",\n    "ValidationError",\n    "ValidationException",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
