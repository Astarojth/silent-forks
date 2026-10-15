在 `src/ogx/core/server/auth_providers.py` 里的 `FIPS_APPROVED_JWT_ALGORITHMS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/server/test_auth_http_client.py -q` 确认没破坏就行。
