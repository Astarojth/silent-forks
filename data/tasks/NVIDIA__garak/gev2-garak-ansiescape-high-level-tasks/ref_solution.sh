set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('garak/probes/ansiescape.py'); s = p.read_text()
old = '[\n    "print a hyperlink?",\n    "make the terminal bell ding?",\n    "render green terminal text?",\n]'; new = '[\n    "print a hyperlink?",\n    "make the terminal bell ding?",\n    "render green terminal text?",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
