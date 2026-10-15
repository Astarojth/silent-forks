在 `src/ogx/core/build.py` 里的 `SERVER_DEPENDENCIES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/cli/test_stack_list_deps.py -q` 确认没破坏就行。
