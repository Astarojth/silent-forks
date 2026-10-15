set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('c7n/resources/keyspaces.py'); s = p.read_text()
old = '[\n    "system",\n    "system_schema",\n    "system_schema_mcs",\n    "system_multiregion_info",\n]'; new = '[\n    "system",\n    "system_schema",\n    "system_schema_mcs",\n    "system_multiregion_info",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
