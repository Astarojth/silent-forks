set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/core/server/auth_providers.py'); s = p.read_text()
old = '[\n    "RS256",\n    "RS384",\n    "RS512",\n    "PS256",\n    "PS384",\n    "PS512",\n    "ES256",\n    "ES384",\n    "ES512",\n]'; new = '[\n    "RS256",\n    "RS384",\n    "RS512",\n    "PS256",\n    "PS384",\n    "PS512",\n    "ES256",\n    "ES384",\n    "ES512",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
