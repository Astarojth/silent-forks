在 `garak/probes/packagehallucination.py` 里的 `stub_prompts` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/probes/test_probes_packagehallucination.py -q` 确认没破坏就行。
