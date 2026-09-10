"""Finalize user-facing delivery records after successful promotion."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project'
final=ROOT/'deliverables/final/kara-no-hako--16x9--round2-approved-r1.mkv'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
manifest=load(P/'final-manifest.json');assert manifest['outputSha256']==sha(final)
state=load(P/'build-state.json');state.update(stage='delivered',renderAuthorization=True)
state['renderResult'].update(finalPromotion='completed',final=final.relative_to(ROOT).as_posix(),finalSha256=sha(final))
state['currentReview']['status']='approved-merged-rendered-delivered'
write(P/'build-state.json',state)
print(json.dumps({'stage':'delivered','final':str(final),'sha256':sha(final),'bytes':final.stat().st_size},ensure_ascii=False))
