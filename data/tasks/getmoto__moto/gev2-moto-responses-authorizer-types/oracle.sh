set -e
grep -qF "zz_extra_entry" "moto/apigateway/responses.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_core/test_responses.py -q 2>&1 | tail -3
