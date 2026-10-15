set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('litellm/types/router.py'); s = p.read_text()
old = '[\n    "development",\n    "staging",\n    "production",\n]'; new = '[\n    "development",\n    "staging",\n    "production",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
