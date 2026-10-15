set -e
grep -qF "zz_extra_entry" "troposphere/validators/eks.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_eks.py -q 2>&1 | tail -3
