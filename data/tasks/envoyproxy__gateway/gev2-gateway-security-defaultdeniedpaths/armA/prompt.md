在 `internal/gatewayapi/luavalidator/security.go` 里的 `defaultDeniedPaths` 切片末尾加一项 `zz_extra_entry`。改完跑一下 `go test ./internal/gatewayapi/luavalidator/ -count=1` 确认没破坏就行。
