from __future__ import annotations
import json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'; x=json.loads(F.read_text(encoding='utf-8'))['frames']; f=next(a for a in x if a['id']=='l050'); c=next(a for a in f['grammarCards'] if a['token']=='なんて'); c['functionZh']='轻微列举；带感叹'; F.write_text(json.dumps({'schemaVersion':3,'frames':x},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
