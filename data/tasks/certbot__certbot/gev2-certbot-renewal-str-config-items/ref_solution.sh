set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('certbot/src/certbot/_internal/renewal.py'); s = p.read_text()
old = '["config_dir", "logs_dir", "work_dir", "user_agent",\n                    "server", "account", "authenticator", "installer",\n                    "deploy_hook", "pre_hook", "post_hook", "http01_address",\n                    "preferred_chain", "key_type", "elliptic_curve",\n                    "preferred_profile", "required_profile"]'; new = '["config_dir", "logs_dir", "work_dir", "user_agent",\n                    "server", "account", "authenticator", "installer",\n                    "deploy_hook", "pre_hook", "post_hook", "http01_address",\n                    "preferred_chain", "key_type", "elliptic_curve",\n                    "preferred_profile", "required_profile", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
