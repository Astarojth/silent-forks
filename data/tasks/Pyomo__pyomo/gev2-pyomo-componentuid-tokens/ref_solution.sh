set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('pyomo/core/base/componentuid.py'); s = p.read_text()
old = '[\n    "WORD",  # unquoted string\n    "STRING",  # quoted string\n    "NUMBER",  # raw number\n    "STAR",  # either * or **\n    "PICKLE",  # a pickled index object\n]'; new = '[\n    "WORD",  # unquoted string\n    "STRING",  # quoted string\n    "NUMBER",  # raw number\n    "STAR",  # either * or **\n    "PICKLE",  # a pickled index object, "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
