在 `moto/core/errors.py` 里的 `COMMON_ERROR_CODES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_core/test_errors.py -q` 确认没破坏就行。
