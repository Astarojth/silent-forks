在 `privacyidea/webui/login.py` 里的 `DEFAULT_LANGUAGE_LIST` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_api_hide_version.py -q` 确认没破坏就行。
