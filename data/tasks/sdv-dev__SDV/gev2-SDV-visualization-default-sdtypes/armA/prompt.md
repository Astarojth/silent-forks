在 `sdv/metadata/visualization.py` 里的 `DEFAULT_SDTYPES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/unit/evaluation/test_multi_table.py -q` 确认没破坏就行。
