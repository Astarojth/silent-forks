set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('smart_open/utils.py'); s = p.read_text()
old = '["s3", "s3n", "s3a", "gcs", "gs"]'; new = '["s3", "s3n", "s3a", "gcs", "gs", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
