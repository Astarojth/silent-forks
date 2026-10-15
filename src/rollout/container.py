"""Docker helpers shared by the task runner."""
import re, subprocess

SNAPSHOT_PY = r'''
import os,sys,hashlib,json
root=sys.argv[1]; out={}
for dp,dn,fn in os.walk(root):
    dn[:] = [d for d in dn if d != '.git']
    for f in fn:
        p=os.path.join(dp,f)
        try:
            if os.path.islink(p): out[os.path.relpath(p,root)]={'link':os.readlink(p)}; continue
            h=hashlib.sha256()
            with open(p,'rb') as fh:
                for chunk in iter(lambda: fh.read(1<<20), b''): h.update(chunk)
            out[os.path.relpath(p,root)]={'sha256':h.hexdigest(),'size':os.path.getsize(p),'mtime':os.path.getmtime(p)}
        except Exception as e: out[os.path.relpath(p,root)]={'err':str(e)}
print(json.dumps(out))
'''

PATH_TOKEN = re.compile(r'[A-Za-z0-9_./-]+')

def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, errors='replace', **kw)

def dexec(c, cmd, workdir=None, stdin=None, timeout=None):
    base = ['docker', 'exec', '-i'] + (['-w', workdir] if workdir else []) + [c, 'bash', '-lc', cmd]
    return subprocess.run(base, capture_output=True, text=True, errors='replace', input=stdin, timeout=timeout)
