set -e
grep -qF "zz_extra_entry" "internal/gatewayapi/luavalidator/security.go" || { echo "entry missing"; exit 1; }
go test ./internal/gatewayapi/luavalidator/ -count=1 2>&1 | tail -3
