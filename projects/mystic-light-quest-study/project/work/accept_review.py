"""Apply the user's explicit 全部采纳 decision to the sealed proposal set."""
import copy
import hashlib
import json
from pathlib import Path
from integrate_review import get, put, card_text

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    frames_path=P/'frames.json'; before=frames_path.read_bytes()
    audit=load(P/'review/assisted-review-audit.json')
    assert sha(frames_path)==audit['baseFrameSha256'], 'Draft changed; do not overwrite user edits'
    for record in [*audit['proposalFiles'],audit['integration']]:
        assert sha(ROOT/record['file'])==record['sha256'], 'Sealed evidence changed'
    proposals=load(P/'review/recommended-proposals.json')
    assert proposals['baseFrameSha256']==sha(frames_path)
    doc=load(frames_path); original=copy.deepcopy(doc)
    by_id={f['id']:f for f in doc['frames']}
    for c in proposals['changes']:
        assert get(by_id[c['frameId']],c['field'])==c['old']
    for c in proposals['changes']: put(by_id[c['frameId']],c['field'],c['new'])
    for old,new in zip(original['frames'],doc['frames']):
        assert old['caption']['translationZh']==new['caption']['translationZh']
        assert old['caption']['japanese']==new['caption']['japanese']
        assert old['displayUnits']==new['displayUnits']
        assert (old['startMs'],old['endMs'])==(new['startMs'],new['endMs'])
        new['status']='approved'
        new['reviewProtection']={'scope':['grammarCards','caption.furigana','caption.romaji','caption.translationZh'],'basis':'user-approved assisted review','userWording':'全部采纳'}
        for card in new['grammarCards']:
            card['status']='approved'
            card['reviewStatus']='user-approved-assisted'
    backup=P/'review/frames-before-approved-merge.json'
    assert not backup.exists(), 'Approval merge already attempted; inspect before rerunning'
    backup.write_bytes(before)
    write(frames_path,doc)
    merged={'schemaVersion':2,'userWording':'全部采纳','scope':'all',
            'framesBeforeSha256':hashlib.sha256(before).hexdigest(),'framesAfterSha256':sha(frames_path),
            'mergedProposalFiles':['project/review/recommended-proposals.json'],
            'sourceProposalFiles':[r['file'] for r in audit['proposalFiles']],
            'recommendedProposalSha256':sha(P/'review/recommended-proposals.json'),
            'mergedFieldBundles':len(proposals['changes']),'frameCount':len(doc['frames']),
            'cardCount':sum(len(f['grammarCards']) for f in doc['frames']),
            'metadataChanges':'Mark the user-approved assisted content as approved and protect it against later automated replacement.',
            'preserved':['QMTS whole-line Chinese','Japanese original','QRC timing and display units']}
    write(P/'review/merge-log.json',merged)
    write(P/'review/review-decision.json',{'schemaVersion':2,'content':'approved','scope':'all','renderAuthorized':False,'userWording':'全部采纳','frameSha256':sha(frames_path),'assistedReviewAuditSha256':sha(P/'review/assisted-review-audit.json'),'mergeLogSha256':sha(P/'review/merge-log.json')})
    functions={}
    md=['# Mystic Light Quest · 已确认审核版','', '用户确认：全部采纳。42句、136张词卡。整句中文保留QMTS；视频尚未授权渲染。','', '词卡顺序：原词｜读音｜罗马音｜含义或功能｜词性。','']
    for f in doc['frames']:
        md += [f"## {f['id']} · {f['startMs']/1000:.3f}s",'',f['caption']['japanese'],'',f"中文（QMTS）：{f['caption']['translationZh']}",'']
        for c in f['grammarCards']:
            md += ['- '+card_text(c)]
            if 'functionZh' in c: functions.setdefault(c['token'],set()).add(c['functionZh'])
        if not f['grammarCards']: md += ['纯英文：保留歌词与高亮，不生成词卡、假名或罗马音。']
        md+=['']
    (ROOT/'deliverables/review/mystic-light-quest-study-approved-review.md').write_text('\n'.join(md),encoding='utf-8')
    write(P/'review/particle-function-table.json',{'schemaVersion':2,'status':'approved','userWording':'全部采纳','functions':{k:sorted(v) for k,v in functions.items()}})
    state=load(P/'build-state.json'); state['stage']='review_approved'
    state['notes'].append('User 全部采纳: applied all integrated proposals, protected 42 lines / 136 cards; content approved, final rendering not authorized.')
    write(P/'build-state.json',state)
    print(json.dumps(merged,ensure_ascii=False))

if __name__=='__main__':main()
