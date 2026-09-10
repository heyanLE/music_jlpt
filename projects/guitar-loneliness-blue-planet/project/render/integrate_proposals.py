"""Build a separate, unapproved preview snapshot; never mutate active frames."""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'project'
SKILL = Path('C:/Users/eke_l/.codex/skills/japanese-song-study-video')
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def locate(obj, field):
    keys = field.split('.')
    for key in keys[:-1]: obj = obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj, int(keys[-1]) if isinstance(obj,list) else keys[-1]
def get(obj, field):
    parent,key=locate(obj,field)
    return parent.get(key) if isinstance(parent,dict) else parent[key]
def put(obj, field, value):
    parent,key=locate(obj,field); parent[key]=copy.deepcopy(value)

def main():
    baseline_path=P/'review/proposal-markdown-baseline.json'
    if baseline_path.exists():
        baseline=load(baseline_path)
        assert hashlib.sha256((ROOT/baseline['file']).read_bytes()).hexdigest()==baseline['sha256'], 'Import human Markdown edits before regenerating review.'
    raw=(P/'frames.json').read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    base=json.loads(raw); proposed=copy.deepcopy(base)
    originals={f['id']:f for f in base['frames']}; frames={f['id']:f for f in proposed['frames']}
    roles={role:load(P/f'proposals/{role}.json') for role in ('grammar','translation','lexical')}
    applied=[]; resolutions=[]
    for role, doc in roles.items():
        assert doc['baseFrameSha256']==sha, role
        assert set(doc['scope']['frameIds'])==set(frames),role
        for change in doc['changes']:
            assert get(originals[change['frameId']],change['field'])==change['old'],(role,change['frameId'],change['field'])
    for role in ('grammar','translation'):
        for c in roles[role]['changes']:
            put(frames[c['frameId']],c['field'],c['new'])
            applied.append({'role':role,'frameId':c['frameId'],'field':c['field']})
    for c in roles['lexical']['changes']:
        f=frames[c['frameId']]; old=originals[c['frameId']]
        if c['field']=='grammarCards':
            result=[]
            for mapping,new in zip(c['cardMapping'],c['new']):
                indices=mapping['sourceCardIndices']
                if len(indices)==1 and old['grammarCards'][indices[0]]['token']==new['token']:
                    card=copy.deepcopy(f['grammarCards'][indices[0]])
                    for key,val in new.items():
                        if val!=old['grammarCards'][indices[0]].get(key): card[key]=copy.deepcopy(val)
                else:
                    card=copy.deepcopy(new)
                    resolutions.append({'frameId':f['id'],'token':card['token'],'sourceCardIndices':indices,'resolution':'Use explicit coordinated whole-token semantics, never concatenate meanings of fragments.'})
                result.append(card)
            f['grammarCards']=result
        elif re.fullmatch(r'grammarCards\.\d+',c['field']):
            card=get(f,c['field'])
            for key,val in c['new'].items():
                if val!=c['old'].get(key): card[key]=copy.deepcopy(val)
        else: put(f,c['field'],c['new'])
        applied.append({'role':'lexical','frameId':c['frameId'],'field':c['field']})
    # Grammar's post-regrouping notes describe whole expressions, not base indices.
    for note in roles['grammar'].get('recommendedNotes',[]):
        if 'newToken' not in note: continue
        for fid in note['frameIds']:
            for card in frames[fid]['grammarCards']:
                if card['token']==note['newToken']:
                    for key in ('grammarStructureZh','functionZh'):
                        if key in note: card[key]=note[key]
    for f in proposed['frames']:
        for card in f['grammarCards']:
            if card.get('functionZh'): card.pop('zhMeaning',None)
            card['status']='integrated-proposal-unapproved'
            card['reviewRequired']=True
            value=card.get('functionZh',card.get('zhMeaning',''))
            assert value and '待联网' not in value and '整语：' not in value,(f['id'],card['token'],value)
    for fid, token, meaning in [('l029','何か','某种东西'),('l021','なんとなく','漫不经心')]:
        card=next(c for c in frames[fid]['grammarCards'] if c['token']==token)
        resolutions.append({'frameId':fid,'token':token,'old':card['zhMeaning'],'new':meaning,'resolution':'Translation-role second-pass review: keep token meaning concise and exclude the following predicate.'})
        card['zhMeaning']=meaning
    policy_path=P/'review/concise-card-policy.json'
    concise_changes=[]
    if policy_path.exists():
        policy=load(policy_path)
        for f in proposed['frames']:
            for i,card in enumerate(f['grammarCards']):
                field='functionZh' if card.get('functionZh') else 'zhMeaning'
                old=card[field]
                new=policy['meaningReplacements'].get(old,old)
                if old!=new:
                    card[field]=new
                    concise_changes.append({'frameId':f['id'],'field':f'grammarCards.{i}.{field}','token':card['token'],'old':old,'new':new})
        write(P/'review/concise-card-change-log.json',{'schemaVersion':1,'userWording':policy['userWording'],'scope':policy['scope'],'changes':concise_changes,'sentenceChineseUnchangedByThisOperation':True})
        grammar_changes=[]
        for f in proposed['frames']:
            for i,card in enumerate(f['grammarCards']):
                old=card.get('grammarStructureZh',''); new=old
                for before,after in policy.get('grammarReplacements',{}).items():
                    new=new.replace(before,after)
                if old!=new:
                    card['grammarStructureZh']=new
                    grammar_changes.append({'frameId':f['id'],'field':f'grammarCards.{i}.grammarStructureZh','token':card['token'],'old':old,'new':new})
        write(P/'review/grammar-label-change-log.json',{'schemaVersion':1,'userWording':policy.get('grammarUserWording',''),'scope':'Grammar labels only; preserve inflection details, meanings, readings and timing. Not blanket proposal acceptance.','changes':grammar_changes})
    proposed['proposalMetadata']={'baseFrameSha256':sha,'status':'unapproved','notRenderAuthority':True}
    write(P/'review/frames-proposed.json',proposed)
    report={'schemaVersion':2,'reviewRole':'integration','status':'completed','baseFrameSha256':sha,'sourceProposals':[f'project/proposals/{r}.json' for r in roles],'oldValuesVerified':len(applied),'conflicts':resolutions,'unresolved':[{'frameId':'l023','token':'300mm','issue':'Unit reading さんびゃくみり needs listening confirmation; QQ romanization retains literal mm.'}],'recommendedChanges':applied,'proposedSnapshot':'project/review/frames-proposed.json','activeFramesUnchanged':True,'contentApproval':False}
    if policy_path.exists():
        report['userDirectedStyleRevision']={'policy':'project/review/concise-card-policy.json','sha256':hashlib.sha256(policy_path.read_bytes()).hexdigest(),'changes':len(concise_changes),'log':'project/review/concise-card-change-log.json'}
        report['userDirectedStyleRevision']['grammarLabelChanges']=len(grammar_changes)
        report['userDirectedStyleRevision']['grammarLabelLog']='project/review/grammar-label-change-log.json'
    write(P/'review/integration-report.json',report)
    lines=['# 吉他与孤独与蓝色星球 — 多角色审核提案','', '状态：尚未采纳。原始 frames.json 未修改；以下为 48 句的拟采用内容，可直接在本 Markdown 修改。','', '## 优先核对','', '- l004「何」读 なに；l028「弾いたら」唱读 はじいたら。','- l020–021：换 Elixir 琴弦也是漫不经心地做；原中文“不如人意”与なんとなく不符。','- l023：300mm 补词卡与罗马音，暂读 さんびゃくみり，单位唱读需听音确认。','- なんとなく、にとっちゃ、何か、なんで等整体分词；助词显示功能，不显示机械词义。','- l041：后半「聴けよ」是加强的命令，不统一翻成敬语请求。','']
    if policy_path.exists():
        lines[4:4]=['词卡释义规则：只显示简短词义或功能，不展开歌词上下文；同形词保留本句对应的用法。整句中文不因精简词卡而更改。','词性规则：不显示动词段数或类别，统一称动词；保留变形说明，ば形统一称假定形。','']
    for f in proposed['frames']:
        original=originals[f['id']]; cap=f['caption']
        lines += [f"## {f['id']} · {cap['japanese']}",'',f"暂定中文：{cap.get('translationZh','')}",'']
        if cap.get('translationZh')!=original['caption'].get('translationZh'):
            lines += [f"QQ 原中文：{original['caption'].get('translationZh','')}",'']
        for card in f['grammarCards']:
            annotation=f"；外来词：{card['sourceWord']}" if card.get('sourceWord') else ''
            lines += [f"- {card['token']}｜{card.get('reading','')}｜{card.get('romaji','')} → {card.get('functionZh',card.get('zhMeaning',''))}｜{card.get('grammarStructureZh','')}{annotation}"]
        lines += ['']
    target=ROOT/'deliverables/review/智能复审-待采纳.md'
    target.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write(P/'review/proposal-markdown-baseline.json',{'file':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'baseFrameSha256':sha,'snapshotSha256':hashlib.sha256((P/'review/frames-proposed.json').read_bytes()).hexdigest()})
    assert (P/'frames.json').read_bytes()==raw
    print(json.dumps({'lines':len(frames),'cards':sum(len(f['grammarCards']) for f in frames.values()),'changesValidated':len(applied),'review':str(target)},ensure_ascii=False))

if __name__=='__main__':main()
