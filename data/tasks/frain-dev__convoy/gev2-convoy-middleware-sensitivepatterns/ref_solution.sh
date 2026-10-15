set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('internal/pkg/middleware/middleware.go'); s = p.read_text()
old = 'var sensitivePatterns = []string{\n\t"-secret",\n\t"-token",\n\t"-signature",\n\t"-key",\n\t"-credential",\n\t"-password",\n}'; new = 'var sensitivePatterns = []string{\n\t"-secret",\n\t"-token",\n\t"-signature",\n\t"-key",\n\t"-credential",\n\t"-password",\n\t"zz_extra_entry",\n}'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
