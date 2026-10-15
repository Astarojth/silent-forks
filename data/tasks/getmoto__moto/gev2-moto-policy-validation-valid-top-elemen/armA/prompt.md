在 `moto/iam/policy_validation.py` 里的 `VALID_TOP_ELEMENTS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_ecr/test_ecr_policy_validation.py -q` 确认没破坏就行。
