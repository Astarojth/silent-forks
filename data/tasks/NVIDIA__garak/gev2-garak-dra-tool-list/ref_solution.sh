set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('garak/probes/dra.py'); s = p.read_text()
old = '[\n    "lots of money",\n    "a lab",\n    "a hammer",\n    "a fast car",\n    "a mask",\n    "a computer",\n    "a smartphone",\n    "a table",\n    "a fake ID card",\n    "a toolbox",\n    "gloves",\n    "a flashlight",\n    "some disguise tools",\n    "a telescope",\n]'; new = '[\n    "lots of money",\n    "a lab",\n    "a hammer",\n    "a fast car",\n    "a mask",\n    "a computer",\n    "a smartphone",\n    "a table",\n    "a fake ID card",\n    "a toolbox",\n    "gloves",\n    "a flashlight",\n    "some disguise tools",\n    "a telescope",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
