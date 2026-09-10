from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'
x=json.loads(F.read_text(encoding='utf-8')); f=next(v for v in x['frames'] if v['id']=='l006'); c=next(v for v in f['grammarCards'] if v['token']=='見えなくなった')
c.pop('functionZh',None); c.update({'zhMeaning':'变得看不见了；不再能看见','grammarStructureZh':'动词否定＋なる过去式','posZh':'变化表达','status':'human-corrected'}); c.setdefault('fieldProvenance',{})['meaningOrFunction']='user-confirmed whole-expression correction'
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
