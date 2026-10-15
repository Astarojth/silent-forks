在 `certbot/src/certbot/_internal/renewal.py` 里的 `BOOL_CONFIG_ITEMS` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest certbot/src/certbot/_internal/tests/renewal_test.py -q` 确认没破坏就行。
