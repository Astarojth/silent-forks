在 `sdv/single_table/utils.py` 里的 `IGNORED_DICT_KEYS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/unit/data_processing/test_utils.py -q` 确认没破坏就行。
