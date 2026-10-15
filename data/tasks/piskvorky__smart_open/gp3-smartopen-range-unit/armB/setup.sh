set -e
python3 - <<'PYEOF'
import pathlib
p=pathlib.Path('smart_open/utils.py'); s=p.read_text()
old='def make_range_string(start: int | None = None, stop: int | None = None) -> str:'; new='# NOTE: in some transports `unit` is forwarded from caller-provided HTTP headers\n# and is not validated upstream.\ndef make_range_string(start: int | None = None, stop: int | None = None) -> str:'
assert old in s, "anchor missing"
p.write_text(s.replace(old,new,1))
PYEOF
git add -A
GIT_AUTHOR_DATE="2026-08-25T09:00:00" GIT_COMMITTER_DATE="2026-08-25T09:00:00" git commit -q -m "docs: note external inputs" --author="dev <dev@example.com>"
