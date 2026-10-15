在 `dynaconf/base.py` 里的 `RESERVED_ATTRS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/test_base.py -q` 确认没破坏就行。
