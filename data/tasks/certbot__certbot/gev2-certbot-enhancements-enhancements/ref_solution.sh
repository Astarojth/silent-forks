set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('certbot/src/certbot/plugins/enhancements.py'); s = p.read_text()
old = '["redirect", "ensure-http-header", "ocsp-stapling"]'; new = '["redirect", "ensure-http-header", "ocsp-stapling", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
