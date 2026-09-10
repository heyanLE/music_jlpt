from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'
x=json.loads(F.read_text(encoding='utf-8')); f=next(v for v in x['frames'] if v['id']=='l008'); cards=f['grammarCards']; i=next(i for i,c in enumerate(cards) if c['token']=='て')
cards[i:i+2]=[{'token':'ている','reading':'ている','romaji':'te iru','zhMeaning':'正在…；持续处于…状态','grammarStructureZh':'持续表达','posZh':'持续表达','status':'human-corrected','fieldProvenance':{'all':'user-confirmed ている merge'}}]
F.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
