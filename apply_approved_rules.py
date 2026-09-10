import json
from pathlib import Path

root = Path(__file__).parent
data = json.loads((root / 'love2000.frames.annotated.review.json').read_text(encoding='utf-8'))
rules = json.loads((root / 'semantic-chunking-rules.json').read_text(encoding='utf-8'))['mergePatterns']

def merge_cards(cards, pattern, role, pos):
    chars = pattern.replace('〜', '')
    i = 0
    while i < len(cards):
        joined = ''
        end = i
        while end < len(cards) and len(joined) < len(chars):
            joined += cards[end]['token']
            end += 1
        if joined == chars:
            group = cards[i:end]
            merged = dict(group[0])
            merged['token'] = joined
            merged['reading'] = ''.join(x['reading'] for x in group)
            merged['romaji'] = ''.join(x['romaji'] for x in group)
            merged['dictionaryForm'] = joined
            merged['posZh'] = pos
            merged['zhMeaning'] = role
            merged['functionZh'] = role
            merged['jlpt'] = None
            merged['render'] = True
            merged['showJlpt'] = False
            merged['reviewRequired'] = False
            cards[i:end] = [merged]
        i += 1
    return cards

for frame in data['frames']:
    if frame['kind'] != 'lyric':
        continue
    cards = frame['grammarCards']
    for rule in rules:
        cards = merge_cards(cards, rule['pattern'], rule['roleZh'], rule['posZh'])
    if cards and cards[-1]['token'] == 'な' and cards[-1].get('posJa') == '助詞':
        cards[-1]['functionZh'] = '语气强调'
        cards[-1]['zhMeaning'] = '呢'
        cards[-1]['posZh'] = '终助词'
        cards[-1]['reviewRequired'] = False
    if cards and cards[-1]['token'] in {'で', 'て'}:
        cards[-1]['functionZh'] = '中顿（连接后句）'
        cards[-1]['zhMeaning'] = '中顿（连接后句）'
        cards[-1]['posZh'] = '接续助词'
        cards[-1]['reviewRequired'] = False
    for card in cards:
        if card['token'] == '誰':
            card['zhMeaning'] = '谁'
            card['posZh'] = '疑问代词'
            card['reviewRequired'] = False
    frame['grammarCards'] = cards
    frame['caption']['furigana'] = [{'base': c['token'], 'reading': c['reading'], 'romaji': c['romaji']} for c in cards]
    frame['analysisStatus'] = 'approved-rules-applied'
data['reviewStatus'] = 'approved-rules-applied'
data['approvalSource'] = ['reviewedFrameIds', 'annotation-rules.json', 'semantic-chunking-rules.json']
(root / 'love2000.frames.approved.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
