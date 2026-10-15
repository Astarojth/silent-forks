set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/apigateway/responses.py'); s = p.read_text()
old = '["TOKEN", "REQUEST", "COGNITO_USER_POOLS"]'; new = '["TOKEN", "REQUEST", "COGNITO_USER_POOLS", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
