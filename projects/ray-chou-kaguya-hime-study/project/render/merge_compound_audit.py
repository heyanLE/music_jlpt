from __future__ import annotations
import json,re
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'; x=json.loads(F.read_text(encoding='utf-8')); fs={f['id']:f for f in x['frames']}
for c in json.loads((P/'proposals/compound-card-second.json').read_text(encoding='utf-8'))['changes']:
 if c['field']=='grammarCards': fs[c['frameId']]['grammarCards']=c['new']
for c in json.loads((P/'proposals/compound-card-audit.json').read_text(encoding='utf-8'))['changes']:
 m=re.fullmatch(r'grammarCards\.(\d+)',c['field'])
 if m: fs[c['frameId']]['grammarCards'][int(m.group(1))]=c['new']
for f in fs.values():
 for c in f.get('grammarCards',[]):
  if 'zhMeaning' in c and 'functionZh' in c: c.pop('functionZh')
  c['status']='assisted-accepted'
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
