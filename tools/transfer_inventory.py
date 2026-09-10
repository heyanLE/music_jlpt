"""Inventory Git-eligible files and possible secrets without printing secret values."""
import collections
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def inventory():
    raw = subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'], cwd=ROOT, check=True, capture_output=True).stdout
    names = sorted(set(x.decode('utf-8') for x in raw.split(b'\0') if x))
    attributes = subprocess.run(['git','check-attr','--stdin','-z','filter'], input=b'\0'.join(n.encode() for n in names)+b'\0', cwd=ROOT, check=True, capture_output=True).stdout.split(b'\0')
    lfs = {attributes[i].decode() for i in range(0,len(attributes)-2,3) if attributes[i+2]==b'lfs'}
    groups=collections.defaultdict(lambda:{'files':0,'bytes':0,'lfsBytes':0})
    oversized=[]; secrets=[]; entries=[]
    pattern=re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|AKIA[A-Z0-9]{16})')
    for name in names:
        path=ROOT/name
        if not path.is_file(): continue
        size=path.stat().st_size
        group='/'.join(name.split('/')[:2]) if name.startswith('projects/') else name.split('/')[0]
        groups[group]['files']+=1;groups[group]['bytes']+=size
        if name in lfs: groups[group]['lfsBytes']+=size
        if size>100*1024**2 and name not in lfs: oversized.append(name)
        if size<10*1024**2 and path.suffix in ('.json','.py','.md','.js','.mjs','.txt','.yaml','.yml','.ps1','.toml'):
            if pattern.search(path.read_bytes()): secrets.append(name)
        entries.append({'path':name,'bytes':size,'lfs':name in lfs})
    return {'files':len(entries),'bytes':sum(e['bytes'] for e in entries),'lfsBytes':sum(e['bytes'] for e in entries if e['lfs']),'groups':dict(groups),'nonLfsOver100MiB':oversized,'possibleSecretFiles':secrets,'entries':entries,'secretCheck':'Basic token/private-key patterns only; not a full security audit'}
if __name__=='__main__':
    report=inventory(); out=ROOT/'transfer'/'inventory.local.json';out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('entries','groups')},ensure_ascii=False))
