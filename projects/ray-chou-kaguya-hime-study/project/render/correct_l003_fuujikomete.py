from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'
x=json.loads(F.read_text(encoding='utf-8')); f=next(v for v in x['frames'] if v['id']=='l003'); c=next(v for v in f['grammarCards'] if v['token']=='封じ込めて')
c.pop('functionZh',None); c.update({'zhMeaning':'封存起来；深藏起来','grammarStructureZh':'复合动词て形','posZh':'复合动词て形','status':'human-corrected'}); c.setdefault('fieldProvenance',{})['meaningOrFunction']='user-confirmed correction'
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
