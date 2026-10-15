set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdv/multi_table/dayz.py'); s = p.read_text()
old = "[\n    'parent_table_name',\n    'child_table_name',\n    'parent_primary_key',\n    'child_foreign_key',\n]"; new = '[\n    \'parent_table_name\',\n    \'child_table_name\',\n    \'parent_primary_key\',\n    \'child_foreign_key\',\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
