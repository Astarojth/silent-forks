在 `privacyidea/lib/caconnectors/localca.py` 里的 `CRL_REASONS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_api_caconnector.py -q` 确认没破坏就行。
