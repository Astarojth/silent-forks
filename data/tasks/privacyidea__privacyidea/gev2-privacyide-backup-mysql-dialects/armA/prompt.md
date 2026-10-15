在 `privacyidea/cli/pimanage/backup.py` 里的 `MYSQL_DIALECTS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/cli/test_cli_pimanage.py -q` 确认没破坏就行。
