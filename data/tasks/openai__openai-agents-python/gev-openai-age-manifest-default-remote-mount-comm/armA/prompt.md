在 `src/agents/sandbox/manifest.py` 里的 `DEFAULT_REMOTE_MOUNT_COMMAND_ALLOWLIST` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `pytest tests/sandbox/test_manifest.py -q` 确认没破坏就行。
