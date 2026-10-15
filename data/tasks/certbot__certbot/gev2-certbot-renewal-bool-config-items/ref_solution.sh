set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('certbot/src/certbot/_internal/renewal.py'); s = p.read_text()
old = '["must_staple", "allow_subset_of_names", "reuse_key",\n                     "autorenew"]'; new = '["must_staple", "allow_subset_of_names", "reuse_key",\n                     "autorenew", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
