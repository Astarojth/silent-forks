set -e
python3 - <<'PYEOF'
import pathlib
p = pathlib.Path('certbot/src/certbot/_internal/plugins/selection.py'); s = p.read_text()
old = '["webroot", "manual", "standalone", "dns-cloudflare",\n                        "dns-digitalocean", "dns-dnsimple", "dns-dnsmadeeasy", "dns-gehirn",\n                        "dns-google", "dns-linode", "dns-luadns", "dns-nsone", "dns-ovh",\n                        "dns-rfc2136", "dns-route53", "dns-sakuracloud"]'; new = '["webroot", "manual", "standalone", "dns-cloudflare",\n                        "dns-digitalocean", "dns-dnsimple", "dns-dnsmadeeasy", "dns-gehirn",\n                        "dns-google", "dns-linode", "dns-luadns", "dns-nsone", "dns-ovh",\n                        "dns-rfc2136", "dns-route53", "dns-sakuracloud", "zz_extra_entry"]'
assert s.count(old) == 1
p.write_text(s.replace(old, new, 1))
PYEOF
