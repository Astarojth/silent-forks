在 `build_backend/plugins_json.py` 里的 `PLUGINSJSON_COMMENTS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest build_backend/test_plugins_json.py -q` 确认没破坏就行。
