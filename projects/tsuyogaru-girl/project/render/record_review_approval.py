import hashlib,json
from pathlib import Path
root=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl");frames=root/'project'/'frames.json';state=root/'project'/'build-state.json';decision=root/'project'/'review'/'review-decision.json'
sha=hashlib.sha256(frames.read_bytes()).hexdigest()
decision.write_text(json.dumps({'content':'approved','scope':'all','renderAuthorized':False,'frameSha256':sha,'authorizationText':'确认词卡'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
d=json.loads(state.read_text(encoding='utf-8'));d['state']='review_approved';d['next']='await_render_authorization';d.setdefault('activeFiles',{})['reviewDecision']='project/review/review-decision.json';d['notes']=['Cards and QMTS translations are content-approved.','A separate explicit render authorization is required.'];state.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
