set -e
python3 - <<'PYEOF'
from pdm.cli.commands.venv.utils import hash_path
a=hash_path("/some/project"); assert len(a)==8
b=hash_path("/some/project", length=12); assert len(b)==12 and b[:8]==a
print("ok")
PYEOF
