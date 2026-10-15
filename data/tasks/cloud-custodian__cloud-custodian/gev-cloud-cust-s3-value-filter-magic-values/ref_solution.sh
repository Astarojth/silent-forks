set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('c7n/resources/s3.py'); s = p.read_text()
old = "['absent', 'present', 'not-null', 'empty']"; new = '[\'absent\', \'present\', \'not-null\', \'empty\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
