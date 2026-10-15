set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdv/single_table/utils.py'); s = p.read_text()
old = "['fitted', 'distribution', 'type']"; new = '[\'fitted\', \'distribution\', \'type\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
