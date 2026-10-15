在 `c7n/actions/autoscaling.py` 里的 `tag_params` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `uv run pytest tests/test_eventbridge.py -q` 确认没破坏就行。
