set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('moto/ec2/models/vpcs.py'); s = p.read_text()
old = '[\n    "cloudformation",\n    "codepipeline",\n    "dynamodb",\n    "ecr",\n    "firehose",\n    "iot",\n    "kinesis",\n    "redshiftdata",\n    "route53resolver",\n    "s3",\n    "sagemaker",\n]'; new = '[\n    "cloudformation",\n    "codepipeline",\n    "dynamodb",\n    "ecr",\n    "firehose",\n    "iot",\n    "kinesis",\n    "redshiftdata",\n    "route53resolver",\n    "s3",\n    "sagemaker",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
