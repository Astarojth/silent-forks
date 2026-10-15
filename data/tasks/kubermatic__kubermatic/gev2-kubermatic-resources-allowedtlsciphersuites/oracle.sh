set -e
grep -qF "zz_extra_entry" "pkg/resources/resources.go" || { echo "entry missing"; exit 1; }
go test ./pkg/resources/ -count=1 2>&1 | tail -3
