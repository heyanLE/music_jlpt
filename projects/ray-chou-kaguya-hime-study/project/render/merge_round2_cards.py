from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'; x=json.loads(F.read_text(encoding='utf-8')); fs={f['id']:f for f in x['frames']}
for c in json.loads((P/'proposals/lexical-round2.json').read_text(encoding='utf-8'))['changes']:
 f=fs[c['frameId']]
 if c['field']=='grammarCards': f['grammarCards']=c['new']
 elif c['field']=='caption.romaji': f['caption']['romaji']=c['new']
for c in json.loads((P/'proposals/grammar-round2.json').read_text(encoding='utf-8'))['changes']:
 f=fs[c['frameId']]
 if c['field']=='grammarCards':
  tokens=[item['token'] for item in c['old']]; cards=f['grammarCards']; matches=[i for i in range(len(cards)-len(tokens)+1) if [item['token'] for item in cards[i:i+len(tokens)]]==tokens]
  if not matches: continue
  start=matches[0]
  del cards[start:start+len(tokens)]
  cards.insert(start,c['new'])
 else:
  _,i,field=c['field'].split('.'); f['grammarCards'][int(i)][field]=c['new']
for f in fs.values():
 for c in f.get('grammarCards',[]): c['status']='assisted-accepted'
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
