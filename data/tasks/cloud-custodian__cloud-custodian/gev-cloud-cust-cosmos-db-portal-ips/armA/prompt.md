在 `tools/c7n_azure/c7n_azure/resources/cosmos_db.py` 里的 `PORTAL_IPS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tools/c7n_azure/tests_azure/tests_resources/test_cosmos_db.py -q` 确认没破坏就行。
