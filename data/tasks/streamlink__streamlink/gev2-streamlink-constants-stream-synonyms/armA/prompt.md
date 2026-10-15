在 `src/streamlink_cli/constants.py` 里的 `STREAM_SYNONYMS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/cli/main/test_output_stream.py -q` 确认没破坏就行。
