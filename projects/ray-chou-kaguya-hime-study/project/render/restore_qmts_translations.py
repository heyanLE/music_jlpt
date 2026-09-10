from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'; T=P/'timing'/'translation.json'
x=json.loads(F.read_text(encoding='utf-8')); rows=json.loads(T.read_text(encoding='utf-8'))['lines']
for f in x['frames']:
 if f.get('clock')=='output': continue
 matches=[r['text'] for r in rows if f['startMs']-150 <= r['startMs'] < f['endMs']]
 if matches: f['caption']['translationZh']=' '.join(matches); f.setdefault('fieldProvenance',{})['translationZh']='timing/translation.json (QMTS source)'
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
