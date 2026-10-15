set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdv/metadata/visualization.py'); s = p.read_text()
old = "['id', 'numerical', 'categorical', 'datetime', 'boolean']"; new = '[\'id\', \'numerical\', \'categorical\', \'datetime\', \'boolean\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
