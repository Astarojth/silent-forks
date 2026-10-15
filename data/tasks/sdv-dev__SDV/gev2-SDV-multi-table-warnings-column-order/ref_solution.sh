set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdv/metadata/multi_table.py'); s = p.read_text()
old = "['Table Name', 'Column Name', 'sdtype', 'datetime_format']"; new = '[\'Table Name\', \'Column Name\', \'sdtype\', \'datetime_format\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
