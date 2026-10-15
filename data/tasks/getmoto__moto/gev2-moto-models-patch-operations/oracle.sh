set -e
grep -qF "zz_extra_entry" "moto/apigateway/models.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_logs/test_models.py -q 2>&1 | tail -3
