在 `privacyidea/lib/tokens/sshkeytoken.py` 里的 `DEFAULT_ALLOWED_SSH_KEY_TYPES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_migration_b8c9d0e1f2a3.py -q` 确认没破坏就行。
