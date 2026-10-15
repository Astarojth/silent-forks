set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('plugins/hydra_ray_launcher/integration_test_tools/setup_integration_test_ami.py'); s = p.read_text()
old = '[\n    "boto3==1.22.6",\n    "hydra-core>=1.1.2",\n    "ray[default]==1.12.0",\n    # https://github.com/aio-libs/aiohttp/issues/6203\n    "aiohttp==3.8.1",\n    "cloudpickle==2.0.0",\n    "pickle5==0.0.11; python_version < \'3.8.0\'",\n]'; new = '[\n    "boto3==1.22.6",\n    "hydra-core>=1.1.2",\n    "ray[default]==1.12.0",\n    # https://github.com/aio-libs/aiohttp/issues/6203\n    "aiohttp==3.8.1",\n    "cloudpickle==2.0.0",\n    "pickle5==0.0.11; python_version < \'3.8.0\'",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
