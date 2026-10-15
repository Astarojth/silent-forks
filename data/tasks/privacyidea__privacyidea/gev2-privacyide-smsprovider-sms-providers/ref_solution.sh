set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('privacyidea/lib/smsprovider/SMSProvider.py'); s = p.read_text()
old = '[\n    "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",\n    "privacyidea.lib.smsprovider.SipgateSMSProvider.SipgateSMSProvider",\n    "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider",\n    "privacyidea.lib.smsprovider.SmppSMSProvider.SmppSMSProvider",\n    "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",\n    "privacyidea.lib.smsprovider.ScriptSMSProvider.ScriptSMSProvider"]'; new = '[\n    "privacyidea.lib.smsprovider.HttpSMSProvider.HttpSMSProvider",\n    "privacyidea.lib.smsprovider.SipgateSMSProvider.SipgateSMSProvider",\n    "privacyidea.lib.smsprovider.SmtpSMSProvider.SmtpSMSProvider",\n    "privacyidea.lib.smsprovider.SmppSMSProvider.SmppSMSProvider",\n    "privacyidea.lib.smsprovider.FirebaseProvider.FirebaseProvider",\n    "privacyidea.lib.smsprovider.ScriptSMSProvider.ScriptSMSProvider", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
