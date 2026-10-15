set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/api/lib/utils.py'); s = p.read_text()
old = '["ES256", "ES384", "ES512",\n                     "RS256", "RS384", "RS512",\n                     "PS256", "PS384", "PS512"]'; new = '["ES256", "ES384", "ES512",\n                     "RS256", "RS384", "RS512",\n                     "PS256", "PS384", "PS512", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
