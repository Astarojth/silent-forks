set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdv/single_table/dayz.py'); s = p.read_text()
old = "['DAYZ_SPEC_VERSION', 'tables', 'relationships']"; new = '[\'DAYZ_SPEC_VERSION\', \'tables\', \'relationships\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
