set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('internal/gatewayapi/luavalidator/security.go'); s = p.read_text()
old = 'var defaultDeniedPaths = []string{\n\t"/etc",\n\t"/proc",\n\t"/sys",\n\t"/certs",\n\t"/var/run/secrets",\n\t// /var/run is a symlink to /run on Debian-derived (distroless) images.\n\t"/run/secrets",\n}'; new = 'var defaultDeniedPaths = []string{\n\t"/etc",\n\t"/proc",\n\t"/sys",\n\t"/certs",\n\t"/var/run/secrets",\n\t// /var/run is a symlink to /run on Debian-derived (distroless) images.\n\t"/run/secrets",\n\t"zz_extra_entry",\n}'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
