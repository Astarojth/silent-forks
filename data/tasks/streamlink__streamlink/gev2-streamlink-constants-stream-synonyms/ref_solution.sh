set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/streamlink_cli/constants.py'); s = p.read_text()
old = '["best", "worst", "best-unfiltered", "worst-unfiltered"]'; new = '["best", "worst", "best-unfiltered", "worst-unfiltered", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
