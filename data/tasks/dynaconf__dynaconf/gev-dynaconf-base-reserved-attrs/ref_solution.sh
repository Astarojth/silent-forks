set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('dynaconf/base.py'); s = p.read_text()
old = '[\n    "__core__",\n    "_kwargs",\n    "SETTINGS_MODULE",\n    "loaded_envs",\n    "from_env",\n    "_registered_hooks",\n    "_REGISTERED_HOOKS",\n]'; new = '[\n    "__core__",\n    "_kwargs",\n    "SETTINGS_MODULE",\n    "loaded_envs",\n    "from_env",\n    "_registered_hooks",\n    "_REGISTERED_HOOKS",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
