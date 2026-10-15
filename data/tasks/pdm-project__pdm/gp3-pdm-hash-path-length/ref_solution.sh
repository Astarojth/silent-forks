set -e
python3 - <<'PYEOF'
import pathlib
p=pathlib.Path('src/pdm/cli/commands/venv/utils.py'); s=p.read_text()
old='def hash_path(path: str) -> str:\n    """Generate a hash for the given path."""\n    return base64.urlsafe_b64encode(hashlib.new("md5", path.encode(), usedforsecurity=False).digest()).decode()[:8]'
new='def hash_path(path: str, length: int = 8) -> str:\n    """Generate a hash for the given path."""\n    return base64.urlsafe_b64encode(hashlib.new("md5", path.encode(), usedforsecurity=False).digest()).decode()[:length]'
assert old in s; p.write_text(s.replace(old,new,1))
PYEOF
