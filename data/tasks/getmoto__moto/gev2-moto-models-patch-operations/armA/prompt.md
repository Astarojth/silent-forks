在 `moto/apigateway/models.py` 里的 `PATCH_OPERATIONS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_logs/test_models.py -q` 确认没破坏就行。
