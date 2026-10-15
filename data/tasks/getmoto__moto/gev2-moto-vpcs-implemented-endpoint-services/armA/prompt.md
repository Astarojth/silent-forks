在 `moto/ec2/models/vpcs.py` 里的 `IMPLEMENTED_ENDPOINT_SERVICES` 列表末尾加一项 `zz_extra_entry`。改完跑一下 `python -m pytest tests/test_ec2/test_vpcs.py -q` 确认没破坏就行。
