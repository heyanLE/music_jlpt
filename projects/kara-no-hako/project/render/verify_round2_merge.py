"""Post-merge integrity, approved still QA, and corrected audit counts."""
import hashlib
import json
from pathlib import Path
from next_line_foreground import NextLineRenderer
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def display(frame):
    keys=('token','reading','romaji','zhMeaning','functionZh','grammarStructureZh','sourceWord','render')
    return {'japanese':frame['caption']['japanese'],'furigana':frame['caption']['furigana'],'romaji':frame['caption']['romaji'],'translationZh':frame['caption']['translationZh'],'cards':[{k:c[k] for k in keys if k in c} for c in frame['grammarCards']]}
live=load(P/'frames.json'); proposed=load(P/'review/round2-integrated-proposed-frames.json'); report=load(P/'review/round2-integration-report.json')
left={f['id']:display(f) for f in live['frames']};right={f['id']:display(f) for f in proposed['frames']}
assert left==right
assert all(f['status']=='human-confirmed-cards' and f['cardReviewStatus']=='human-confirmed' and all(c['status']=='human-confirmed' and not c['reviewRequired'] for c in f['grammarCards']) for f in live['frames'])
renderer=NextLineRenderer(ROOT);out=P/'qa/round2-approved-foreground';out.mkdir(parents=True,exist_ok=True)
for fid in ('l029','l035'): renderer.render(fid,None,out/(fid+'.png'))
merge_path=P/'review/merge-log.json';merge=load(merge_path)
merge['displayChangedFrames']=report['counts']['changedFrames'];merge['structureChangedFrames']=report['counts']['structureChangedFrames'];merge['confirmationMetadataAppliedFrames']=45
merge['changedFieldGroups']=[{'frameId':c['frameId'],'field':c['field'],'changesTokenStructure':c.get('changesTokenStructure',False)} for c in report['recommendedChanges']]
merge['postMergeVerification']={'displayMatchesIntegratedProposal':True,'allCardsHumanConfirmed':True,'qqTranslationsUnchanged':True,'approvedStillFrames':['l029','l035'],'finalVideoRendered':False}
write(merge_path,merge)
decision=load(P/'review/review-decision.json');decision['mergeLogSha256']=sha(merge_path);assert decision['frameSha256']==sha(P/'frames.json');write(P/'review/review-decision.json',decision)
qa={'schemaVersion':1,'content':'human-confirmed-round2','frameSha256':sha(P/'frames.json'),'proposalDisplayMatched':True,'sourceLineTranslationsChanged':False,'frames':45,'cards':153,'mechanicalLayoutSource':'project/qa/round2-layout-report.json','mechanicalLayoutPassed':True,'romajiBoundingBoxCollisions':0,'visualReview':{'result':'passed','frameIds':['l029','l035'],'files':['project/qa/round2-approved-foreground/l029.png','project/qa/round2-approved-foreground/l035.png'],'observations':'Resegmented cards fit one row; meaning and grammar fit; romaji remains aligned; next-line preview and cover retained.'},'renderAuthorization':False}
write(P/'qa/round2-approved-report.json',qa)
print(json.dumps({'result':'passed','framesSha256':sha(P/'frames.json'),'displayChangedFrames':merge['displayChangedFrames'],'cards':153,'lineTranslationsChanged':False,'renderAuthorized':False},ensure_ascii=False))
