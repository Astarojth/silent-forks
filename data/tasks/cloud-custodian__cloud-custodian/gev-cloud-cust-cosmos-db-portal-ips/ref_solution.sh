set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('tools/c7n_azure/c7n_azure/resources/cosmos_db.py'); s = p.read_text()
old = "['104.42.195.92',\n              '40.76.54.131',\n              '52.176.6.30',\n              '52.169.50.45',\n              '52.187.184.26']"; new = '[\'104.42.195.92\',\n              \'40.76.54.131\',\n              \'52.176.6.30\',\n              \'52.169.50.45\',\n              \'52.187.184.26\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
