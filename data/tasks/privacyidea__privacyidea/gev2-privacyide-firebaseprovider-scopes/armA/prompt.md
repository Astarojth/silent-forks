在 `privacyidea/lib/smsprovider/FirebaseProvider.py` 里的 `SCOPES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_api_ttype.py -q` 确认没破坏就行。
