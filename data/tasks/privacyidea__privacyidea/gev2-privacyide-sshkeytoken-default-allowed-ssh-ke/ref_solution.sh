set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/lib/tokens/sshkeytoken.py'); s = p.read_text()
old = '["ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256",\n                                 "sk-ecdsa-sha2-nistp256@openssh.com", "sk-ssh-ed25519@openssh.com"]'; new = '["ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256",\n                                 "sk-ecdsa-sha2-nistp256@openssh.com", "sk-ssh-ed25519@openssh.com", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
