在 `privacyidea/lib/smsprovider/SMSProvider.py` 里的 `SMS_PROVIDERS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_api_validate_triggered.py -q` 确认没破坏就行。
