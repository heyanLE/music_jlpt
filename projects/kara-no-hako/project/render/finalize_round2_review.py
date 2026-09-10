"""Record final integration checks before sealing. Does not approve or merge content."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
baseline='7e730357a5d9a6adf121d4f23c7fc86a263769209d78a4a8444f2fba122f48d6'
assert sha(P/'frames.json')==baseline
report=load(P/'review/round2-integration-report.json')
qa=load(P/'qa/round2-layout-report.json')
assert qa['framesSha256']==sha(P/'review/round2-integrated-proposed-frames.json')
assert qa['result']=='passed-mechanical'
assert not any(r['romajiBoundingBoxOverlaps'] for r in qa['rows'])
qa['visualReview']={'result':'passed-sampled','frameIds':['l029','l035'],'observations':'Both resegmented frames inspected. Cover/next-line preview preserved; card fields fit; no romaji collision. Transparent foreground-only samples, not final background composites.'}
write(P/'qa/round2-layout-report.json',qa)
report['checks'].update(all45ProposedLayoutsPassed=True,romajiBoundingBoxesNoOverlap=True,sampledStructureVisualPassed=True)
report['proposalFrameSha256']=sha(P/'review/round2-integrated-proposed-frames.json')
report['qaReport']='project/qa/round2-layout-report.json'
report['qaReportSha256']=sha(P/'qa/round2-layout-report.json')
report['sourceTranslationIssuesFile']='deliverables/review/kara-no-hako-round2-source-translations.md'
report['decisionRequired']='explicit-user-content-decision; no content merged and no render authorized'
for role in ('lexical','grammar','translation'):
    d=load(P/f'proposals/round2/{role}.json')
    assert len(d['frameAssessments'])==45
    assert len(set(a['frameId'] for a in d['frameAssessments']))==45
write(P/'review/round2-integration-report.json',report)
state=load(P/'build-state.json')
state.update(stage='draft_ready',activeReviewRound='round2',renderAuthorization=False)
state['currentReview']={'status':'completed-awaiting-user','fullReview':'deliverables/review/kara-no-hako-round2-review.md','changesOnly':'deliverables/review/kara-no-hako-round2-changes.md','sourceChineseSeparate':'deliverables/review/kara-no-hako-round2-source-translations.md','integration':'project/review/round2-integration-report.json','liveFrameSha256':baseline,'counts':report['counts']}
write(P/'build-state.json',state)
paths=[P/'review/round2-integration-report.json',P/'review/round2-integrated-proposed-frames.json',*(P/'proposals/round2').glob('*.json'),*(ROOT/'deliverables/review').glob('*round2*.md')]
for path in paths:
    raw=path.read_bytes();assert not raw.startswith(b'\xef\xbb\xbf'),path
    assert '\ufffd' not in raw.decode('utf-8'),path
print(json.dumps({'content':'proposal-only','framesUnchanged':True,'utf8CheckedFiles':len(paths),'counts':report['counts']},ensure_ascii=False))
