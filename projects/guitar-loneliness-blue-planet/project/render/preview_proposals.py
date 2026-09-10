"""Static review-only proof from a separate proposed snapshot."""
import json
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
from foreground_renderer import ForegroundRenderer
p=ROOT/'project'
frames=json.loads((p/'review/frames-proposed.json').read_text(encoding='utf-8'))['frames']
r=ForegroundRenderer(ROOT,1920,1080)
r.frames={f['id']:f for f in frames}
r.ordered_ids=[f['id'] for f in frames]
out=p/'qa/proposed-static-r2'
out.mkdir(parents=True,exist_ok=True)
errors=[]
for f in frames:
    try:r.render(f['id'],None,out/f"{f['id']}.png")
    except Exception as e:errors.append({'frameId':f['id'],'error':str(e)})
report={'status':'passed' if not errors else 'failed','kind':'unapproved-proposal-only','frameCount':len(frames),'errors':errors}
(p/'qa/proposed-layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
