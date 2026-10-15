set -e
grep -qF "zz_extra_entry" "dynaconf/default_settings.py" || { echo "entry missing"; exit 1; }
python -m pytest tests_functional/issues/575_603_666_690__envvar_with_template_substitution/app_test.py -q 2>&1 | tail -3
