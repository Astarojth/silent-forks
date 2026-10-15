set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/providers/registry/inference.py'); s = p.read_text()
old = '[\n    "accelerate",\n    "fairscale",\n    "torch",\n    "torchvision",\n    "transformers",\n    "zmq",\n    "lm-format-enforcer",\n    "sentence-transformers",\n    "torchao==0.8.0",\n    "fbgemm-gpu-genai==1.1.2",\n]'; new = '[\n    "accelerate",\n    "fairscale",\n    "torch",\n    "torchvision",\n    "transformers",\n    "zmq",\n    "lm-format-enforcer",\n    "sentence-transformers",\n    "torchao==0.8.0",\n    "fbgemm-gpu-genai==1.1.2",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
