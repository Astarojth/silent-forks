在 `privacyidea/api/lib/utils.py` 里的 `TRUSTED_JWT_ALGOS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_lib_logging.py -q` 确认没破坏就行。
