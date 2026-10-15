set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/core/utils.py'); s = p.read_text()
old = '[\n    "Jan",\n    "Feb",\n    "Mar",\n    "Apr",\n    "May",\n    "Jun",\n    "Jul",\n    "Aug",\n    "Sep",\n    "Oct",\n    "Nov",\n    "Dec",\n]'; new = '[\n    "Jan",\n    "Feb",\n    "Mar",\n    "Apr",\n    "May",\n    "Jun",\n    "Jul",\n    "Aug",\n    "Sep",\n    "Oct",\n    "Nov",\n    "Dec",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
