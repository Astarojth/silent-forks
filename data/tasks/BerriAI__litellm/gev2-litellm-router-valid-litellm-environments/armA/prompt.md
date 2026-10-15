在 `litellm/types/router.py` 里的 `VALID_LITELLM_ENVIRONMENTS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_litellm/types/test_router.py -q` 确认没破坏就行。
