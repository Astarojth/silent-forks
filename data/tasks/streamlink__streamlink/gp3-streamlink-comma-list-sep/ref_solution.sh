set -e
python3 - <<'PYEOF'
import pathlib
p=pathlib.Path('src/streamlink/utils/args.py'); s=p.read_text()
old='def comma_list(values: str) -> list[str]:\n    return [val.strip() for val in values.split(",")]'
new='def comma_list(values: str, sep: str = ",") -> list[str]:\n    return [val.strip() for val in values.split(sep)]'
assert old in s; p.write_text(s.replace(old,new,1))
PYEOF
