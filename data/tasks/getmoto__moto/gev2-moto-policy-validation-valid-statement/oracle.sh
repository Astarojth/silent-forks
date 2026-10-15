set -e
grep -qF "zz_extra_entry" "moto/iam/policy_validation.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_ecr/test_ecr_policy_validation.py -q 2>&1 | tail -3
