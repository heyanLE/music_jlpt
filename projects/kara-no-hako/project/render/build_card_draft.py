"""Build an explicitly unapproved draft from source lyrics and authored study chunks."""
import copy
import hashlib
import json
import re
from pathlib import Path
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'project'
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def hira(s): return ''.join(chr(ord(c)-96) if 'ァ' <= c <= 'ヶ' else c for c in s)
converter = kakasi()
def roman(reading, token):
    overrides = {'は':'wa','を':'o','へと':'e to','地図には':'chizu ni wa','とは':'to wa','のですが':'no desu ga','のでしょうか':'no deshou ka'}
    return overrides.get(token, ''.join(p['hepburn'] for p in converter.convert(reading)))
def ruby_spans(token, reading, offset):
    pieces = re.findall(r'[一-龯々]+|[^一-龯々]+', token)
    pattern = '^' + ''.join('(.+?)' if re.fullmatch(r'[一-龯々]+', p) else re.escape(hira(p)) for p in pieces) + '$'
    matched = re.match(pattern, reading)
    if not matched: raise ValueError(f'Cannot align ruby: {token} {reading}')
    out, cursor, group = [], offset, 1
    for p in pieces:
        if re.fullmatch(r'[一-龯々]+', p):
            out.append({'base':p,'reading':matched.group(group),'start':cursor,'end':cursor+len(p)})
            group += 1
        cursor += len(p)
    return out

def main():
    frames = read(PROJECT / 'frames.json')
    source = read(PROJECT / 'render/draft-card-data.json')
    functions = {}
    for frame in frames['frames']:
        spec = source[frame['id']]
        if isinstance(spec, str): spec = copy.deepcopy(source[spec])
        text, cursor, cards, rubies = frame['caption']['japanese'], 0, [], []
        for values in spec:
            token, reading, meaning, grammar = values[:4]
            start = text.find(token, cursor)
            if start < 0 or text[cursor:start].strip(): raise ValueError((frame['id'], token, cursor))
            cursor = start + len(token)
            card = {'token':token,'reading':reading,'romaji':roman(reading,token),'grammarStructureZh':grammar,'render':True,'status':'draft','reviewRequired':True,
                    'fieldProvenance':{'token':'authored learning chunk draft','reading':'draft with QQ kana/roma reference','meaningOrFunction':'draft informed by supplied QMTS; not dictionary-verified','grammarStructureZh':'authored draft; role review pending'}}
            key = 'functionZh' if len(values)>4 and values[4] else 'zhMeaning'
            card[key] = meaning
            if key == 'functionZh': functions.setdefault(token, set()).add(meaning)
            cards.append(card)
            rubies.extend(ruby_spans(token, reading, start))
        if re.sub(r'[\s？?!！、。]', '', text[cursor:]): raise ValueError((frame['id'],'uncovered tail'))
        frame['grammarCards'] = cards
        frame['sourceRomaji'] = frame.get('sourceRomaji', frame['caption']['romaji'])
        frame['caption']['romaji'] = ' '.join(c['romaji'] for c in cards)
        frame['caption']['furigana'] = rubies
        frame['status'] = 'draft'
        frame['translationStatus'] = 'source-imported'
        frame['fieldProvenance']['translationZh'] = 'supplied lyrics_qmts.qrc; exact source translation retained'
    write(PROJECT / 'frames.json', frames)
    write(PROJECT / 'particle-functions.json', {'schemaVersion':1,'status':'draft','functions':{k:sorted(v) for k,v in functions.items()}})
    digest = hashlib.sha256((PROJECT / 'frames.json').read_bytes()).hexdigest()
    write(PROJECT / 'review/draft-manifest.json', {'schemaVersion':1,'frameSha256':digest,'frameCount':len(frames['frames']),'cardCount':sum(len(f['grammarCards']) for f in frames['frames']),'contentApproved':False})
    lines = ['# 空の箱｜待审核词卡', '', '整句中文原样取自你提供的 QQ 音乐翻译文件。以下分词、读音、词义和结构均为草稿，尚未人工确认。', '', '优先核查：l011 今日的实际唱读；l025 所為；l024/l044/l045 明日；l029–l030 跨句修饰关系。', '']
    for frame in frames['frames']:
        lines += [f"## {frame['id']}　{frame['caption']['japanese']}", '', f"暂定中文：{frame['caption']['translationZh']}", '', '词卡：', '']
        for c in frame['grammarCards']:
            lines += [f"- {c['token']}（{c['reading']} / {c['romaji']}）——{c.get('functionZh',c.get('zhMeaning'))}；{c['grammarStructureZh']}"]
        lines += ['']
    target = ROOT / 'deliverables/review/kara-no-hako-review.md'
    target.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'frameHash':digest,'frames':len(frames['frames']),'cards':sum(len(f['grammarCards']) for f in frames['frames']),'review':str(target)}, ensure_ascii=False))

if __name__ == '__main__': main()
