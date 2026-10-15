set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/lib/caconnectors/msca.py'); s = p.read_text()
old = '["unspecified", "keyCompromise", "CACompromise",\n               "affiliationChanged", "superseded", "cessationOfOperation"]'; new = '["unspecified", "keyCompromise", "CACompromise",\n               "affiliationChanged", "superseded", "cessationOfOperation", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
