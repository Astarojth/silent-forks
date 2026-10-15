在 `troposphere/validators/eks.py` 里的 `VALID_TAINT_EFFECT` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_eks.py -q` 确认没破坏就行。
