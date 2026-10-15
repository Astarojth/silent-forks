在 `src/ogx/core/server_tls.py` 里的 `FIPS_APPROVED_CIPHERS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/server/test_tls_config.py -q` 确认没破坏就行。
