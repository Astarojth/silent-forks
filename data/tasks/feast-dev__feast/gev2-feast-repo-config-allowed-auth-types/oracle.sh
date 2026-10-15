set -e
grep -qF "zz_extra_entry" "sdk/python/feast/repo_config.py" || { echo "entry missing"; exit 1; }
pytest sdk/python/tests/unit/infra/scaffolding/test_repo_config.py -q 2>&1 | tail -3
