"""Validate independent role proposals and create a proposal-only review bundle."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'project'
BASE = 'e062cef34bd38d5f9b37309eb2085df3b46969abb568b3bad9de587d3f01d047'

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def parts(field):
    return [int(x) if x.isdigit() else x for x in re.sub(r'\[(\d+)\]', r'.\1', field).split('.')]

def get(obj, field):
    for key in parts(field): obj = obj[key]
    return obj

def put(obj, field, value):
    keys = parts(field)
    for key in keys[:-1]: obj = obj[key]
    obj[keys[-1]] = copy.deepcopy(value)

def card_text(c):
    result = f"{c['token']}｜{c['reading']}｜{c['romaji']}｜{c.get('zhMeaning',c.get('functionZh'))}｜{c['grammarStructureZh']}"
    return result + (f"｜来源词：{c['sourceWord']}" if c.get('sourceWord') else '')

def main():
    original = (P/'frames.json').read_bytes()
    assert hashlib.sha256(original).hexdigest() == BASE
    frames = load(P/'frames.json')['frames']
    before = {f['id']: f for f in frames}
    proposed = copy.deepcopy(before)
    docs = {role: load(P/f'proposals/{role}.json') for role in ['lexical','grammar','translation']}
    touched = {}
    overlaps = []
    for role, doc in docs.items():
        assert doc['baseFrameSha256'] == BASE
        assert set(doc['scope']['frameIds']) == set(before)
        for c in doc['changes']:
            assert not c['field'].startswith(('caption.translation', 'caption.japanese', 'displayUnits'))
            assert get(before[c['frameId']],c['field']) == c['old'], (role,c)
    # Apply independent grammar edits before the explicit structural bundle.
    for role in ['grammar','lexical','translation']:
        for c in docs[role]['changes']:
            fid, field = c['frameId'], c['field']
            keys = parts(field)
            for old_keys, old_role in touched.get(fid, []):
                if keys[:len(old_keys)] == old_keys or old_keys[:len(keys)] == keys:
                    identical = get(proposed[fid],field) == c['new']
                    assert fid == 'l025' or identical, ('unresolved conflict',fid,field,old_role,role)
                    overlaps.append({'frameId':fid,'field':field,'roles':[old_role,role], 'resolution':'Identical proposal; apply once.' if identical else 'Use the whole idiom bundle; final label and meaning resolved explicitly below.'})
            put(proposed[fid],field,c['new'])
            touched.setdefault(fid,[]).append((keys,role))
    # All three roles support the idiom. Keep the requested concise POS row.
    c = proposed['l025']['grammarCards'][0]
    assert c['token'] == '心が躍れば'
    c['grammarStructureZh'] = '动词短语'
    c['zhMeaning'] = '如果心情雀跃'
    recommended = []
    for fid, new in proposed.items():
        old = before[fid]
        assert old['caption']['translationZh'] == new['caption']['translationZh']
        assert old['displayUnits'] == new['displayUnits']
        for field in ['grammarCards','caption.furigana','caption.romaji']:
            if get(old,field) != get(new,field):
                recommended.append({'frameId':fid,'field':field,'old':get(old,field),'new':get(new,field),'changesTokenStructure':fid=='l025','evidence':[f'Independent lexical/grammar/translation proposals for {fid}; integration-report.json'], 'confidence':0.95})
        for card in new['grammarCards']:
            assert ('zhMeaning' in card) != ('functionZh' in card)
        for ruby in new['caption']['furigana']:
            assert new['caption']['japanese'][ruby['start']:ruby['end']] == ruby['base']
    groups = {}
    for fid, frame in proposed.items():
        jp = frame['caption']['japanese']
        if jp in groups: assert groups[jp] == frame['grammarCards'], ('repeat mismatch',fid)
        else: groups[jp] = frame['grammarCards']
    rec_path = 'project/review/recommended-proposals.json'
    write(ROOT/rec_path, {'schemaVersion':2,'reviewRole':'integration','status':'proposal-only','baseFrameSha256':BASE,'scope':{'frameIds':list(before)},'changes':recommended})
    report = {'schemaVersion':2,'reviewRole':'integration','status':'completed','baseFrameSha256':BASE,
        'sourceProposalFiles':[f'project/proposals/{r}.json' for r in docs],
        'sourceChangeCounts':{r:len(d['changes']) for r,d in docs.items()},
        'conflicts':overlaps,
        'resolutions':[{'frameId':'l025','decision':'Merge 心が躍れば, meaning 如果心情雀跃, concise POS 动词短语. Use lexical ruby re-anchoring.','reason':'All roles support idiomatic whole-block meaning; grammar and translation refine the lexical structural companion fields.'},
                       {'frameId':'l027','decision':'Retain the provisional comparative reading of ように; remove redundant 往事 from its card because 過去 is separate.','reason':'The lyric/QMTS context permits this reading; do not overstate it as a uniquely certain analysis.'}],
        'recommendedProposalSet':rec_path,'recommendedFieldBundles':len(recommended),
        'reviewedFrames':42,'draftCards':138,'recommendedCards':sum(len(f['grammarCards']) for f in proposed.values()),
        'checks':{'allOldValuesMatch':True,'allRoleScopesComplete':True,'wholeLineQmtsUnchanged':True,'qrcTimingUnchanged':True,'rubyAnchorsValid':True,'repeatedCardsConsistent':True},
        'renderBlockers':['User content approval outstanding','Fix ruby/romaji collisions documented in project/qa/pre-render-layout-actions.md','Explicit final render authorization outstanding']}
    write(P/'review/integration-report.json',report)
    md=['# Mystic Light Quest · 多角色合并审阅','',
        '状态：提案，尚未合入正式词卡。42句、138张原草稿词卡已由词汇、文法、语境译义三个角色全覆盖审核；建议合并后136张。',
        '整句中文全部保留QMTS来源。本文件只展示有修改建议的句子和词卡；未列出的部分建议保留。词卡顺序：原词｜读音｜罗马音｜含义或功能｜词性。','',
        '## 重点','', '- l018：行ける按歌曲唱读改成ゆける／yukeru，同步汉字注音。',
        '- l025：心／が／躍れば合成「心が躍れば」，完整解释为「如果心情雀跃」，词性「动词短语」。',
        '- 其余：精简末行词性，修正跨卡重复释义；长词块仍解释完整词义及活用含义。','']
    for fid, new in proposed.items():
        old=before[fid]
        if old==new: continue
        md += [f'## {fid} · {old["startMs"]/1000:.3f}s','',old['caption']['japanese'],'',f'暂定中文（QMTS不改）：{old["caption"]["translationZh"]}','']
        if fid=='l025':
            md += ['建议合并：心 ＋ が ＋ 躍れば','',f'- 建议：{card_text(new["grammarCards"][0])}','']
        else:
            for a,b in zip(old['grammarCards'],new['grammarCards']):
                if a==b: continue
                md += [f'- 原：{card_text(a)}',f'  - 建议：{card_text(b)}','']
        if old['caption']['furigana']!=new['caption']['furigana']:
            md += ['注音联动：'+('行 → ゆ；其余假名不重复注音。' if fid=='l018' else '合并后重新绑定心、躍的汉字注音；原字符及时间不变。'),'']
    md += ['## 来源与只读备注','', '- l025惯用语：[小学馆《デジタル大辞泉》心が躍る](https://kotobank.jp/word/心が躍る-500464)。',
        '- 外来语オアシス继续标注oasis；所有英文保持原位置，无词卡、假名或罗马音。',
        '- l006、l018、l020、l025、l026、l027、l038的QMTS有诗意转述或扩写；来源整句不改。词卡依据其实际日文词块释义。',
        '- l027「ように」暂按比况理解，不将此解释表述为唯一可能。',
        '- 版式另有待修复：l008/l029的注音、罗马音相邻重叠，正式渲染前处理；不影响本次内容审阅。','',
        '确认方式：可回复“采纳全部提案”，或列出要改的句号与词卡。此处未请求最终视频渲染授权。','']
    (ROOT/'deliverables/review/mystic-light-quest-study-consolidated-review.md').write_text('\n'.join(md),encoding='utf-8')
    assert (P/'frames.json').read_bytes()==original
    print(json.dumps({'roles':report['sourceChangeCounts'],'recommendedBundles':len(recommended),'affectedFrames':len(touched),'cards':report['recommendedCards'],'framesUnchanged':True},ensure_ascii=False))

if __name__=='__main__': main()
