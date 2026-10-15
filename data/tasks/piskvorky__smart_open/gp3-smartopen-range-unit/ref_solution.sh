set -e
python3 - <<'PYEOF'
import pathlib
p=pathlib.Path('smart_open/utils.py'); s=p.read_text()
old='def make_range_string(start: int | None = None, stop: int | None = None) -> str:'
new='def make_range_string(start: int | None = None, stop: int | None = None, unit: str = "bytes") -> str:'
assert old in s
s=s.replace(old,new,1)
old2='return f"bytes={start_str}-{stop_str}"'
new2='return f"{unit}={start_str}-{stop_str}"'
assert old2 in s; p.write_text(s.replace(old2,new2,1))
PYEOF
