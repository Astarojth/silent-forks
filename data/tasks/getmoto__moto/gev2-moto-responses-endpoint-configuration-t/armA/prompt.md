在 `moto/apigateway/responses.py` 里的 `ENDPOINT_CONFIGURATION_TYPES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_core/test_responses.py -q` 确认没破坏就行。
