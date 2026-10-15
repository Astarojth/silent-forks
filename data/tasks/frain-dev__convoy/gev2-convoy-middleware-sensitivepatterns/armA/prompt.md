在 `internal/pkg/middleware/middleware.go` 里的 `sensitivePatterns` 切片末尾加一项 `zz_extra_entry`。改完跑一下 `go test ./internal/pkg/middleware/ -count=1` 确认没破坏就行。
