set -e
grep -qF "zz_extra_entry" "internal/pkg/middleware/middleware.go" || { echo "entry missing"; exit 1; }
go test ./internal/pkg/middleware/ -count=1 2>&1 | tail -3
