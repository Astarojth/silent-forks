set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdk/python/feast/image_utils.py'); s = p.read_text()
old = '["weighted_sum", "concatenate", "average"]'; new = '["weighted_sum", "concatenate", "average", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
