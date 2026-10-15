在 `c7n/resources/keyspaces.py` 里的 `SYSTEM_KEYSPACES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/test_keyspaces.py -q` 确认没破坏就行。
