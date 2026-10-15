在 `dynaconf/cli.py` 里的 `EXTS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/test_cli.py -q` 确认没破坏就行。
