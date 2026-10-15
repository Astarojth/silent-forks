在 `smart_open/utils.py` 里的 `WORKAROUND_SCHEMES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/test_utils.py -q` 确认没破坏就行。
