在 `dynaconf/default_settings.py` 里的 `core_loaders` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests_functional/issues/575_603_666_690__envvar_with_template_substitution/app_test.py -q` 确认没破坏就行。
