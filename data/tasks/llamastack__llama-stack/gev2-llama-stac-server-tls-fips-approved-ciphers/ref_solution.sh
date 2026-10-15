set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/core/server_tls.py'); s = p.read_text()
old = '[\n    "ECDHE-ECDSA-AES128-GCM-SHA256",\n    "ECDHE-RSA-AES128-GCM-SHA256",\n    "ECDHE-ECDSA-AES256-GCM-SHA384",\n    "ECDHE-RSA-AES256-GCM-SHA384",\n    "DHE-RSA-AES128-GCM-SHA256",\n    "DHE-RSA-AES256-GCM-SHA384",\n]'; new = '[\n    "ECDHE-ECDSA-AES128-GCM-SHA256",\n    "ECDHE-RSA-AES128-GCM-SHA256",\n    "ECDHE-ECDSA-AES256-GCM-SHA384",\n    "ECDHE-RSA-AES256-GCM-SHA384",\n    "DHE-RSA-AES128-GCM-SHA256",\n    "DHE-RSA-AES256-GCM-SHA384",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
