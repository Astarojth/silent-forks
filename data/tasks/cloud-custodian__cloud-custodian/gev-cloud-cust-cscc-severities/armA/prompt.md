在 `tools/c7n_gcp/c7n_gcp/actions/cscc.py` 里的 `SEVERITIES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tools/c7n_gcp/tests/test_cscc.py -q` 确认没破坏就行。
