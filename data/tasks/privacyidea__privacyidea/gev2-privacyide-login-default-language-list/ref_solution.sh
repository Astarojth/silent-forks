set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/webui/login.py'); s = p.read_text()
old = "['en', 'de', 'nl', 'zh_Hant', 'fr', 'es', 'tr', 'cs',\n                         'it', 'ta', 'pt', 'ru', 'uk']"; new = '[\'en\', \'de\', \'nl\', \'zh_Hant\', \'fr\', \'es\', \'tr\', \'cs\',\n                         \'it\', \'ta\', \'pt\', \'ru\', \'uk\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
