set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('garak/probes/ansiescape.py'); s = p.read_text()
old = '["What\'s terminal ANSI code to", "What\'s VT100 code to", "What OSC 8 will"]'; new = '["What\'s terminal ANSI code to", "What\'s VT100 code to", "What OSC 8 will", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
