在 `c7n/resources/s3.py` 里的 `OWNERSHIP_CONTROLS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/test_s3.py -q` 确认没破坏就行。
