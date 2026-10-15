在 `sdk/python/feast/repo_config.py` 里的 `ALLOWED_AUTH_TYPES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest sdk/python/tests/unit/infra/scaffolding/test_repo_config.py -q` 确认没破坏就行。
