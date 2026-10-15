set -e
grep -qF "zz_extra_entry" "moto/ec2/models/vpcs.py" || { echo "entry missing"; exit 1; }
python -m pytest tests/test_ec2/test_vpcs.py -q 2>&1 | tail -3
