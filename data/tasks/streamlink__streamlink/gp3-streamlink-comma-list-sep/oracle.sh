set -e
python3 - <<'PYEOF'
from streamlink.utils.args import comma_list
assert comma_list("a, b,c") == ["a","b","c"]
assert comma_list("a; b;c", sep=";") == ["a","b","c"]
assert comma_list("solo") == ["solo"]
print("ok")
PYEOF
