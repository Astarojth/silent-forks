set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdv/_utils.py'); s = p.read_text()
old = "['categorical', 'numerical', 'datetime', 'boolean']"; new = '[\'categorical\', \'numerical\', \'datetime\', \'boolean\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
