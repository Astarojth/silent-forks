在 `sdv/_utils.py` 里的 `MODELABLE_SDTYPES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/unit/evaluation/test__utils.py -q` 确认没破坏就行。
