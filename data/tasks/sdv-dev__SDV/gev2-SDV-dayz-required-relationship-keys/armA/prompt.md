在 `sdv/multi_table/dayz.py` 里的 `REQUIRED_RELATIONSHIP_KEYS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/unit/multi_table/test_dayz.py -q` 确认没破坏就行。
