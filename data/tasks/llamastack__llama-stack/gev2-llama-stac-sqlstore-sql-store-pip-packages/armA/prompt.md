在 `src/ogx/core/storage/sqlstore/sqlstore.py` 里的 `sql_store_pip_packages` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/utils/sqlstore/test_sqlstore.py -q` 确认没破坏就行。
