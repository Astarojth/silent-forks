set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('build_backend/plugins_json.py'); s = p.read_text()
old = '[\n    "DO NOT MODIFY!",\n    "This file was auto-generated and its checksum is validated before loading.",\n    "If you want to modify existing plugins, then please see the plugin-sideloading or developing docs:",\n    "https://streamlink.github.io/",\n]'; new = '[\n    "DO NOT MODIFY!",\n    "This file was auto-generated and its checksum is validated before loading.",\n    "If you want to modify existing plugins, then please see the plugin-sideloading or developing docs:",\n    "https://streamlink.github.io/",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
