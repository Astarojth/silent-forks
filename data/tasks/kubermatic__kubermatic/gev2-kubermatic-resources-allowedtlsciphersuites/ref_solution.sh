set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('pkg/resources/resources.go'); s = p.read_text()
old = 'var allowedTLSCipherSuites = []string{\n\t// TLS 1.3 cipher suites\n\t"TLS_AES_128_GCM_SHA256",\n\t"TLS_AES_256_GCM_SHA384",\n\t"TLS_CHACHA20_POLY1305_SHA256",\n\t// TLS 1.0 - 1.2 cipher suites\n\t"TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",\n\t"TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",\n\t"TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",\n\t"TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",\n\t"TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",\n\t"TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305",\n}'; new = 'var allowedTLSCipherSuites = []string{\n\t// TLS 1.3 cipher suites\n\t"TLS_AES_128_GCM_SHA256",\n\t"TLS_AES_256_GCM_SHA384",\n\t"TLS_CHACHA20_POLY1305_SHA256",\n\t// TLS 1.0 - 1.2 cipher suites\n\t"TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",\n\t"TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",\n\t"TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305",\n\t"TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",\n\t"TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",\n\t"TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305",\n\t"zz_extra_entry",\n}'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
