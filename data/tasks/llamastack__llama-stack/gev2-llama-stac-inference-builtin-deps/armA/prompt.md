在 `src/ogx/providers/registry/inference.py` 里的 `BUILTIN_DEPS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/unit/cli/test_stack_utils.py -q` 确认没破坏就行。
