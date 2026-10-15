在 `privacyidea/lib/policy.py` 里的 `DEFAULT_PREFERRED_CLIENT_MODE_LIST` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_api_offline_no_token.py -q` 确认没破坏就行。
