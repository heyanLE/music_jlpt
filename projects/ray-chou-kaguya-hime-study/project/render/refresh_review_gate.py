from __future__ import annotations
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'project'; F=P/'frames.json'; h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=P/'review/merge-log.json'; x=json.loads(m.read_text(encoding='utf-8')); x['framesAfterSha256']=h(F); x['finalAcceptedCorrections']='Long-token card audit accepted; QMTS full-line Chinese retained.'; m.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
d=P/'review/review-decision.json'; y=json.loads(d.read_text(encoding='utf-8')); y.update({'content':'approved','scope':'all cards; QMTS translations locked','renderAuthorized':False,'userWording':'确认采纳；按当前审核版渲染','frameSha256':h(F),'mergeLogSha256':h(m)}); d.write_text(json.dumps(y,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
