set -e
grep -qF "zz_extra_entry" "sdk/python/feast/image_utils.py" || { echo "entry missing"; exit 1; }
pytest sdk/python/tests/unit/test_image_utils.py -q 2>&1 | tail -3
