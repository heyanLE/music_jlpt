import json
import re
from pathlib import Path

from fugashi import Tagger
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parent
tagger, kks = Tagger(), kakasi()
PARTICLES = {
    "は": "提示主题", "が": "标示主语或焦点", "を": "标示动作对象", "に": "标示到达点、时间或对象",
    "で": "标示动作场所或手段", "と": "标示并列、引用或共同对象", "も": "表示“也、都”",
    "の": "表示所属或名词修饰", "へ": "标示移动方向", "から": "表示起点或原因", "まで": "表示终点或范围",
    "より": "表示比较基准", "や": "列举事物", "ね": "寻求认同", "よ": "加强告知语气", "か": "表示疑问"
}
POS = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "連体詞": "连体词", "接続詞": "连接词", "助詞": "助词", "助動詞": "助动词", "感動詞": "感叹词", "接頭辞": "前缀", "接尾辞": "后缀"}
SKIP = re.compile(r"^(詞：|曲：|もうどうなってもいいや\s*-|\(Ooh\)|\(Yeah)")

def hira(value):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in (value or ''))

def roma(value):
    return ' '.join(x['hepburn'] for x in kks.convert(value)).lower()

def translation(start, rows):
    nearby = [x for x in rows if abs(x['startMs'] - start) <= 1800]
    return min(nearby, key=lambda x: abs(x['startMs'] - start))['text'] if nearby else '（待人工核对翻译）'

frames_doc = json.loads((ROOT / 'frames.json').read_text(encoding='utf8'))
translations = json.loads((ROOT / 'timing' / 'translation.json').read_text(encoding='utf8'))
for frame in frames_doc['frames']:
    text = frame['caption']['japanese']
    frame['caption']['translationZh'] = translation(frame['startMs'], translations)
    if SKIP.search(text) or not re.search(r'[ぁ-んァ-ヶ一-龯]', text):
        frame['caption']['furigana'] = []
        frame['caption']['romaji'] = ''
        frame['grammarCards'] = []
        frame['fieldProvenance'] = {'caption.translationZh': 'qmts-draft'}
        frame['analysisStatus'] = 'draft'
        continue
    cards, furi, romas = [], [], []
    for word in tagger(text):
        surface = word.surface
        if not surface or not re.search(r'[ぁ-んァ-ヶ一-龯]', surface):
            continue
        feature, pos = word.feature, word.feature.pos1 or '記号'
        reading = hira(feature.kana or feature.pron or surface)
        card = {'token': surface, 'reading': reading, 'romaji': roma(reading), 'posZh': POS.get(pos, '符号'), 'status': 'draft', 'fieldProvenance': 'morphological-analysis-draft'}
        if pos == '助詞': card['functionZh'] = PARTICLES.get(surface, '语法功能待人工核对')
        else: card['zhMeaning'] = '词义待人工核对'
        cards.append(card); romas.append(card['romaji'])
        if re.search(r'[一-龯々]', surface): furi.append({'base': surface, 'reading': reading})
    frame['caption']['furigana'] = furi
    frame['caption']['romaji'] = ' '.join(romas)
    frame['grammarCards'] = cards
    frame['fieldProvenance'] = {'caption.japanese': 'qm', 'caption.romaji': 'morphological-analysis-draft', 'caption.translationZh': 'qmts-draft', 'grammarCards': 'morphological-analysis-draft'}
    frame['analysisStatus'] = 'draft'

(ROOT / 'frames.json').write_text(json.dumps(frames_doc, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
review = ['# もうどうなってもいいや — 学习卡审核草稿', '', '所有中文释义、语法卡及假名均为草稿，尚未人工确认。', '']
for f in frames_doc['frames']:
    c = f['caption']; review += [f"## {f['id']} · {f['startMs']/1000:.3f}s", '', f"日文：{c['japanese']}", f"中文（草稿）：{c['translationZh']}", '']
    for card in f['grammarCards']:
        review.append(f"- {card['token']}（{card['reading']} / {card['romaji']}）：{card.get('functionZh') or card.get('zhMeaning')}；{card['posZh']}（草稿）")
    review.append('')
(ROOT / 'review' / 'mp3-audio-review.md').write_text('\n'.join(review), encoding='utf8')
(ROOT.parent / 'deliverables' / 'review' / 'mou-dou-natte-mo-ii-ya-review.md').write_text('\n'.join(review), encoding='utf8')
print(json.dumps({'frames': len(frames_doc['frames']), 'cards': sum(len(x['grammarCards']) for x in frames_doc['frames'])}, ensure_ascii=False))
