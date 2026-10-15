set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('tools/c7n_gcp/c7n_gcp/actions/cscc.py'); s = p.read_text()
old = "['LOW', 'MEDIUM', 'HIGH', 'SEVERITY_UNSPECIFIED']"; new = '[\'LOW\', \'MEDIUM\', \'HIGH\', \'SEVERITY_UNSPECIFIED\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
