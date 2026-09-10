from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'
x=json.loads(F.read_text(encoding='utf-8'))
for frame in x['frames']:
 for c in frame.get('grammarCards',[]):
  if c.get('grammarStructureZh')=='待语法审阅': c['grammarStructureZh']=c['posZh']='词汇'
  if 'zhMeaning' in c and 'functionZh' in c: c.pop('zhMeaning')
  if 'zhMeaning' not in c and 'functionZh' not in c: c['zhMeaning']='待人工复核'
  c['status']='assisted-accepted' if frame.get('status')!='user-supplied' else c.get('status','user-supplied')
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
