"""Merge the explicitly accepted round-two card set; does not authorize rendering."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
USER_WORDING='采纳第二轮全部词卡提案'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

frames_path=P/'frames.json'; before=sha(frames_path)
EXPECTED_BEFORE='7e730357a5d9a6adf121d4f23c7fc86a263769209d78a4a8444f2fba122f48d6'
if before != EXPECTED_BEFORE:
    decision_path=P/'review/review-decision.json'
    assert decision_path.exists() and load(decision_path).get('userWording')==USER_WORDING
    assert load(decision_path).get('frameSha256')==before
    print(json.dumps({'status':'already-merged','framesSha256':before,'renderAuthorized':False},ensure_ascii=False))
    raise SystemExit(0)
audit_path=P/'review/assisted-review-audit.json'; integration_path=P/'review/round2-integration-report.json'; proposal_path=P/'review/round2-integrated-proposed-frames.json'
audit=load(audit_path); report=load(integration_path); live=load(frames_path); proposed=load(proposal_path)
assert before==report['baseFrameSha256']==audit['baseFrameSha256']
assert audit['integration']['file']=='project/review/round2-integration-report.json'
assert audit['integration']['sha256']==sha(integration_path)
assert report['proposalFrameSha256']==sha(proposal_path)
assert report['checks']['all45ProposedLayoutsPassed']
live_by={f['id']:f for f in live['frames']}; prop_by={f['id']:f for f in proposed['frames']}
assert set(live_by)==set(prop_by)
source_chinese={fid:f['caption']['translationZh'] for fid,f in live_by.items()}
merged_fields=[]
for fid,frame in live_by.items():
    candidate=prop_by[fid]
    assert candidate['caption']['japanese']==frame['caption']['japanese']
    assert candidate['caption']['translationZh']==frame['caption']['translationZh']
    old_cards=copy.deepcopy(frame['grammarCards']); old_romaji=frame['caption']['romaji']
    frame['grammarCards']=copy.deepcopy(candidate['grammarCards'])
    frame['caption']['romaji']=candidate['caption']['romaji']
    frame['status']='human-confirmed-cards'
    frame['cardReviewStatus']='human-confirmed'
    frame['reviewRequired']=False
    frame.setdefault('fieldProvenance',{})['grammarCards']='round2 lexical/grammar/translation review + explicit user acceptance'
    frame['fieldProvenance']['romaji']='round2 lexical review + explicit user acceptance'
    # The user accepted the complete reviewed card set, including keep decisions.
    for card in frame['grammarCards']:
        card['status']='human-confirmed'; card['reviewRequired']=False
        card.setdefault('fieldProvenance',{})['humanConfirmation']='second-round multi-agent card set accepted by user'
    if old_cards!=frame['grammarCards']: merged_fields.append({'frameId':fid,'field':'grammarCards','changed':True})
    if old_romaji!=frame['caption']['romaji']: merged_fields.append({'frameId':fid,'field':'caption.romaji','changed':True})
assert all(f['caption']['translationZh']==source_chinese[fid] for fid,f in live_by.items())
write(frames_path,live); after=sha(frames_path)
merge_log={
  'schemaVersion':2,'reviewRound':'round2','userWording':USER_WORDING,'mergedAt':datetime.now(timezone.utc).isoformat(),
  'scope':'complete round2 integrated card set; QQ sourceTranslationIssues excluded','framesBeforeSha256':before,'framesAfterSha256':after,
  'mergedProposalFiles':['project/proposals/round2/lexical.json','project/proposals/round2/grammar.json','project/proposals/round2/translation.json','project/review/round2-integrated-proposed-frames.json','project/review/round2-integration-report.json'],
  'proposalFrameSha256':sha(proposal_path),'assistedReviewAuditSha256':sha(audit_path),'frameCount':len(live_by),'cardCount':sum(len(f['grammarCards']) for f in live_by.values()),
  'changedFieldGroups':merged_fields,'sourceLineTranslationsChanged':False,'renderAuthorized':False
}
merge_path=P/'review/merge-log.json';write(merge_path,merge_log)
decision={'schemaVersion':2,'content':'approved','scope':'all-second-round-card-proposals','renderAuthorized':False,'userWording':USER_WORDING,'frameSha256':after,'assistedReviewAuditSha256':sha(audit_path),'mergeLogSha256':sha(merge_path),'sourceTranslationIssuesApproved':False}
write(P/'review/review-decision.json',decision)
state=load(P/'build-state.json');state.update(stage='review_approved',renderAuthorization=False,activeReviewRound='round2')
state['currentReview'].update(status='approved-and-merged',liveFrameSha256=after,decision='project/review/review-decision.json',mergeLog='project/review/merge-log.json')
state['notes'].append('User explicitly accepted all second-round card proposals. 153 cards merged and human-confirmed; seven separate QQ line-translation suggestions remain unaccepted; final rendering not authorized.')
write(P/'build-state.json',state)
print(json.dumps({'framesBeforeSha256':before,'framesAfterSha256':after,'frames':len(live_by),'cards':merge_log['cardCount'],'changedFieldGroups':len(merged_fields),'lineTranslationsChanged':False,'renderAuthorized':False},ensure_ascii=False))
