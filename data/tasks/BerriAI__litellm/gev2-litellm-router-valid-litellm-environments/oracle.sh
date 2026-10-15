set -e
grep -qF "zz_extra_entry" "litellm/types/router.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_litellm/types/test_router.py -q 2>&1 | tail -3
