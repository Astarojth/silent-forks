set -e
python3 - <<'PYEOF'
from smart_open.utils import make_range_string
assert make_range_string(1, 20) == "bytes=1-20"
assert make_range_string(1, 20, unit="items") == "items=1-20"
assert make_range_string(5) == "bytes=5-"
print("ok")
PYEOF
