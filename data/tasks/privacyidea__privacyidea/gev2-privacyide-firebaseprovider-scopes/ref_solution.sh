set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/lib/smsprovider/FirebaseProvider.py'); s = p.read_text()
old = "['https://www.googleapis.com/auth/cloud-platform',\n          'https://www.googleapis.com/auth/datastore',\n          'https://www.googleapis.com/auth/devstorage.read_write',\n          'https://www.googleapis.com/auth/firebase',\n          'https://www.googleapis.com/auth/identitytoolkit',\n          'https://www.googleapis.com/auth/userinfo.email']"; new = '[\'https://www.googleapis.com/auth/cloud-platform\',\n          \'https://www.googleapis.com/auth/datastore\',\n          \'https://www.googleapis.com/auth/devstorage.read_write\',\n          \'https://www.googleapis.com/auth/firebase\',\n          \'https://www.googleapis.com/auth/identitytoolkit\',\n          \'https://www.googleapis.com/auth/userinfo.email\', "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
