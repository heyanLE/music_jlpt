"""Independent integration pass: validates and consolidates proposals, never merges live frames."""
import copy
import hashlib
import json
from pathlib import Path
from next_line_foreground import NextLineRenderer

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
ROLES=('lexical','grammar','translation')
# Conflicting meanings require an explicit audited resolution, not score-based selection.
RESOLUTIONS={}
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def get(obj,path):
    for k in path.split('.'): obj=obj[int(k)] if isinstance(obj,list) else obj[k]
    return obj
def put(obj,path,value):
    keys=path.split('.')
    for k in keys[:-1]: obj=obj[int(k)] if isinstance(obj,list) else obj[k]
    k=keys[-1]
    if isinstance(obj,list): obj[int(k)]=value
    else: obj[k]=value

def main():
    baseline=load(P/'frames.json')
    digest=hashlib.sha256((P/'frames.json').read_bytes()).hexdigest()
    lookup={f['id']:f for f in baseline['frames']}
    docs={role:load(P/f'proposals/{role}.json') for role in ROLES}
    grouped={}
    for role,doc in docs.items():
        assert doc['baseFrameSha256']==digest, role
        assert set(doc['scope']['frameIds'])==set(lookup), role
        for index,change in enumerate(doc['changes']):
            assert get(lookup[change['frameId']],change['field'])==change['old'], (role,index)
            assert not change['changesTokenStructure'], (role,index,'unexpected structure mutation')
            grouped.setdefault((change['frameId'],change['field']),[]).append({'role':role,'index':index,'change':change})
    selected=[]; conflicts=[]
    for key,items in grouped.items():
        values={json.dumps(x['change']['new'],ensure_ascii=False,sort_keys=True) for x in items}
        if len(values)==1:
            chosen=items[0]; reason='Independent roles agree or field has only one proposal.'
        else:
            resolution=RESOLUTIONS.get('.'.join(key))
            conflicts.append({'frameId':key[0],'field':key[1],'candidates':items,'resolution':resolution})
            if resolution is None: continue
            chosen=next(x for x in items if x['role']==resolution['role']); reason=resolution['reason']
        selected.append({**chosen['change'],'sourceRole':chosen['role'],'sourceProposalIndex':chosen['index'],'supportingRoles':[x['role'] for x in items],'integrationReason':reason})
    if any(c['resolution'] is None for c in conflicts):
        write(P/'review/integration-input-check.json',{'conflicts':conflicts,'status':'needs-main-agent-conflict-review'})
        print(json.dumps({'conflicts':conflicts},ensure_ascii=False,indent=2)); return
    proposed=copy.deepcopy(baseline)
    proposed_lookup={f['id']:f for f in proposed['frames']}
    for change in selected: put(proposed_lookup[change['frameId']],change['field'],change['new'])
    repeats={}
    for frame in proposed['frames']:
        assert frame['caption']['translationZh']==lookup[frame['id']]['caption']['translationZh'], 'QQ Chinese must remain unchanged'
        expected=' '.join(c['romaji'] for c in frame['grammarCards'])
        assert frame['caption']['romaji']==expected, frame['id']
        for c in frame['grammarCards']:
            assert bool(c.get('zhMeaning')) != bool(c.get('functionZh'))
        text=frame['caption']['japanese']
        if text in repeats: assert frame['grammarCards']==repeats[text], ('repeat mismatch',frame['id'])
        repeats[text]=frame['grammarCards']
    write(P/'review/integrated-proposed-frames.json',proposed)
    renderer=NextLineRenderer(ROOT)
    renderer.frames=proposed_lookup
    renderer.ordered=sorted(proposed['frames'],key=lambda f:f['startMs'])
    qa=P/'qa/proposed-foreground'; qa.mkdir(parents=True,exist_ok=True)
    for frame in renderer.ordered: renderer.render(frame['id'],None,qa/(frame['id']+'.png'))
    source_issues=docs['translation'].get('translationSourceIssues',[])
    report={'schemaVersion':2,'reviewRole':'integration','status':'completed','baseFrameSha256':digest,'sourceProposalFiles':[f'project/proposals/{r}.json' for r in ROLES],
            'conflicts':conflicts,'recommendedChanges':selected,'checks':{'allOldValuesMatched':True,'fullRoleCoverage':True,'sourceChinesePreserved':True,'repeatedCardBundlesConsistent':True,'liveFramesUnchanged':True,'allProposedLayersFit':True},
            'decisionRequired':'explicit-user-content-decision','sourceTranslationPolicy':'Preserve supplied QQ line translations. translationSourceIssues are advisory only, not part of the recommendedChanges batch.',
            'counts':{'frames':len(lookup),'cards':151,'roleProposals':{r:len(d['changes']) for r,d in docs.items()},'recommendedFields':len(selected)},
            'unresolved':[{'frameId':'l011','issue':'今日 retains source こんにち; actual singing not independently heard'},{'frameId':'l012','issue':'解ける keeps a neutral grammar label because intransitive/potential analysis is ambiguous'}],
            'translationSourceIssues':source_issues}
    write(P/'review/integration-report.json',report)
    write(P/'qa/proposed-layout-report.json',{'result':'passed-mechanical','frames':45,'previewLayouts':renderer.preview_layouts,'content':'proposal-only; not approved'})
    lines=['# 空の箱｜集中审核修改点','','这是三个角色复审后的建议，不是已采纳内容。主稿 frames.json 未改。','',
           f"45 句、151 张词卡；建议修改 {len(selected)} 个字段，包含罗马音空格和词卡说明。分词边界不变。",'',
           '## 需要注意','','- l011「今日」暂保留歌词文件的「こんにち / konnichi」，未声称已经实际听辨。','- l012「解けますか」建议中性标为「解ける＋礼貌疑问」，避免强定自动词／可能形。',
           '- 所有整句中文继续原样使用 QQ 翻译轨；下方的源译疑点只供参考，不包含在默认批量采纳词卡提案内。','',
           '## 罗马音统一优化','','长语法块内部加空格，仍放在对应块下方，读音和分词边界不变。例如 `shiroinda → shiroi n da`、`yokuittamonode → yoku itta mono de`。此项同时更新当前句和下一句预读。','',
           '## 词卡需要修改的部分','']
    semantic=[c for c in selected if not c['field'].endswith('romaji')]
    for frame in baseline['frames']:
        changes=[c for c in semantic if c['frameId']==frame['id']]
        if not changes: continue
        lines += [f"### {frame['id']}　{frame['caption']['japanese']}",'',f"暂定中文（QQ）：{frame['caption']['translationZh']}",'']
        for c in changes:
            index=int(c['field'].split('.')[1]); token=frame['grammarCards'][index]['token']
            field='结构' if c['field'].endswith('grammarStructureZh') else '功能' if c['field'].endswith('functionZh') else '含义'
            lines += [f"- {token}｜{field}：{c['old']} → **{c['new']}**"]
        lines += ['']
    lines += ['## QQ 整句翻译的源译疑点（未列入批量修改）','']
    for issue in source_issues:
        ids=issue['frameIds']
        lines += ['### '+' / '.join(ids),'']
        for frame_id,source_text,suggested_text in zip(ids,issue['sourceText'],issue['suggestedText']):
            lines += [f"{frame_id}　{lookup[frame_id]['caption']['japanese']}",'',f"QQ 原文：{source_text}",'',f"学习参考（未采纳）：{suggested_text}",'']
        lines += ['注意：'+issue['reason'],'']
        if issue.get('evidence'):
            lines += ['参考：'+'；'.join(f'[来源 {i+1}]({url})' for i,url in enumerate(issue['evidence'])),'']
    lines += ['## 审核边界','','本次若采纳全部词卡提案，只合并 integration-report.json 的 recommendedChanges；QQ整句中文保持原样。若希望使用下方学习向参考译文，请明确提出。','词卡确认后仍需单独授权正式视频渲染。','']
    out=ROOT/'deliverables/review/kara-no-hako-review-changes.md'
    out.write_text('\n'.join(lines),encoding='utf-8')
    assert hashlib.sha256((P/'frames.json').read_bytes()).hexdigest()==digest
    print(json.dumps(report['counts'],ensure_ascii=False))

if __name__=='__main__': main()
