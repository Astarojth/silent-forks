set -e
python3 - <<'PYEOF'
import pathlib
p=pathlib.Path('src/pdm/cli/commands/venv/utils.py'); s=p.read_text()
old='def hash_path(path: str) -> str:'; new='# NOTE: the desired prefix length is taken from user configuration in some call\n# paths and may be negative or larger than the digest.\ndef hash_path(path: str) -> str:'
assert old in s, "anchor missing"
p.write_text(s.replace(old,new,1))
PYEOF
git add -A
GIT_AUTHOR_DATE="2026-08-25T09:00:00" GIT_COMMITTER_DATE="2026-08-25T09:00:00" git commit -q -m "docs: note external inputs" --author="dev <dev@example.com>"
