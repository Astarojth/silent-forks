set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/cli/pimanage/backup.py'); s = p.read_text()
old = '["mysql", "pymysql", "mysql+pymysql", "mariadb+pymysql"]'; new = '["mysql", "pymysql", "mysql+pymysql", "mariadb+pymysql", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
