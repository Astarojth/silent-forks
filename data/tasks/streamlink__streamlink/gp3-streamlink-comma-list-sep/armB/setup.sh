set -e
python3 - <<'PYEOF'
import pathlib
p=pathlib.Path('src/streamlink/utils/args.py'); s=p.read_text()
old='def comma_list(values: str) -> list[str]:'; new='# NOTE: comma_list is exposed to third-party plugin option parsers; plugin code\n# may pass arbitrary, unvalidated values here.\ndef comma_list(values: str) -> list[str]:'
assert old in s, "anchor missing"
p.write_text(s.replace(old,new,1))
PYEOF
git add -A
GIT_AUTHOR_DATE="2026-08-25T09:00:00" GIT_COMMITTER_DATE="2026-08-25T09:00:00" git commit -q -m "docs: note external inputs" --author="dev <dev@example.com>"
