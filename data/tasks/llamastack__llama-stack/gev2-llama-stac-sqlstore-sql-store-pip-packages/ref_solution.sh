set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/core/storage/sqlstore/sqlstore.py'); s = p.read_text()
old = '["sqlalchemy[asyncio]", "aiosqlite", "asyncpg"]'; new = '["sqlalchemy[asyncio]", "aiosqlite", "asyncpg", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
