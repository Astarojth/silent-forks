在 `moto/core/utils.py` 里的 `EN_MONTHS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_swf/test_utils.py -q` 确认没破坏就行。
