set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('sdk/python/feast/repo_config.py'); s = p.read_text()
old = '["no_auth", "kubernetes", "oidc"]'; new = '["no_auth", "kubernetes", "oidc", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
