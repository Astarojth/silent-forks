在 `pkg/resources/resources.go` 里的 `allowedTLSCipherSuites` 切片末尾加一项 `zz_extra_entry`。改完跑一下 `go test ./pkg/resources/ -count=1` 确认没破坏就行。
