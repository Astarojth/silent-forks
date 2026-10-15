在 `sdk/python/feast/image_utils.py` 里的 `COMBINATION_STRATEGIES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest sdk/python/tests/unit/test_image_utils.py -q` 确认没破坏就行。
