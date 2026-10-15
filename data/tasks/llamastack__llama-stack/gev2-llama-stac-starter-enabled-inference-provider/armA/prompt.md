在 `src/ogx/distributions/starter/starter.py` 里的 `ENABLED_INFERENCE_PROVIDERS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/distribution/test_list_deps_output.py -q` 确认没破坏就行。
