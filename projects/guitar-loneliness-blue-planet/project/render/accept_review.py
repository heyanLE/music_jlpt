"""Apply the user's current explicit acceptance; refuses stale or edited review."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'project'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    wording='确认，需要频谱动画'
    baseline=load(P/'review/proposal-markdown-baseline.json')
    assert sha(ROOT/baseline['file'])==baseline['sha256'],'Import user Markdown edits first'
    assert sha(P/'review/frames-proposed.json')==baseline['snapshotSha256']
    assert sha(P/'frames.json')==baseline['baseFrameSha256'],'Active frames changed'
    before=sha(P/'frames.json'); draft=load(P/'frames.json')
    write(P/'review/frames-before-acceptance.json',draft)
    proposed=load(P/'review/frames-proposed.json');proposed.pop('proposalMetadata',None)
    for f in proposed['frames']:
        f['status']='user-approved'
        for c in f['grammarCards']:
            c['status']='user-approved';c['reviewRequired']=False
    write(P/'frames.json',proposed);after=sha(P/'frames.json')
    log={'schemaVersion':2,'framesBeforeSha256':before,'framesAfterSha256':after,'scope':'all','userWording':wording,'proposalSnapshotSha256':baseline['snapshotSha256'],'sourceProposals':[f'project/proposals/{r}.json' for r in ('lexical','grammar','translation')],'stylePolicies':['project/review/concise-card-policy.json'],'changes':'Accept 48-line integrated snapshot including concise meanings and simplified verb labels. No segmentation, reading, translation or timing edits beyond the reviewed snapshot.'}
    write(P/'review/merge-log.json',log)
    write(P/'review/review-decision.json',{'schemaVersion':2,'content':'approved','scope':'all','renderAuthorized':True,'userWording':wording,'frameSha256':after,'assistedReviewAuditSha256':sha(P/'review/assisted-review-audit.json'),'mergeLogSha256':sha(P/'review/merge-log.json'),'readingNote':'l023 さんびゃくみり is accepted with the reviewed snapshot; no claim of independent listening confirmation.'})
    state=load(P/'build-state.json');state.update(stage='review_approved',renderAuthorization=True)
    state['nextAction']='Render the accepted active frames with the project custom renderer and persistent transparent spectrum; perform QA then promote.'
    state['unresolved']=[];state['notes'].append('User confirmed current cards and spectrum: '+wording)
    write(P/'build-state.json',state)
    print(json.dumps({'acceptedLines':len(proposed['frames']),'frameSha256':after},ensure_ascii=False))
if __name__=='__main__':main()
