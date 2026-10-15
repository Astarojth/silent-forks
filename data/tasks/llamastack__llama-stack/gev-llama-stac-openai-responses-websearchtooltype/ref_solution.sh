set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx_api/openai_responses.py'); s = p.read_text()
old = '["web_search", "web_search_preview", "web_search_preview_2025_03_11", "web_search_2025_08_26"]'; new = '["web_search", "web_search_preview", "web_search_preview_2025_03_11", "web_search_2025_08_26", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
