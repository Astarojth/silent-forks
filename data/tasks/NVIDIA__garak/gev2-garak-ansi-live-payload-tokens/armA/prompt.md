在 `garak/resources/ansi.py` 里的 `LIVE_PAYLOAD_TOKENS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/probes/test_probes_ansiescape.py -q` 确认没破坏就行。
