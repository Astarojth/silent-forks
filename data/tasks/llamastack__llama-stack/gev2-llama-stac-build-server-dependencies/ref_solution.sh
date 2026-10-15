set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('src/ogx/core/build.py'); s = p.read_text()
old = '[\n    "aiosqlite",\n    "fastapi",\n    "fire",\n    "httpx",\n    "uvicorn",\n    "opentelemetry-sdk",\n    "opentelemetry-exporter-otlp-proto-http",\n    "opentelemetry-exporter-otlp-proto-grpc",\n]'; new = '[\n    "aiosqlite",\n    "fastapi",\n    "fire",\n    "httpx",\n    "uvicorn",\n    "opentelemetry-sdk",\n    "opentelemetry-exporter-otlp-proto-http",\n    "opentelemetry-exporter-otlp-proto-grpc",\n    "zz_extra_entry",\n]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
