在 `src/ogx_api/openai_responses.py` 里的 `WebSearchToolTypes` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/integration/agents/test_openai_responses.py -q` 确认没破坏就行。
