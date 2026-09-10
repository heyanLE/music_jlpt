"""Apply confirmed global connective-card conventions without touching other cards."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
PATH = ROOT / 'love2000.frames.approved.json'
data = json.loads(PATH.read_text(encoding='utf-8'))
changed = []

for frame in data['frames']:
    if frame.get('kind') != 'lyric':
        continue
    cards = frame['grammarCards']
    merged, index, did_change = [], 0, False
    while index < len(cards):
        pair = cards[index:index + 2]
        if len(pair) == 2 and pair[0]['token'] == 'だ' and pair[1]['token'] == 'けど':
            merged.append({
                'token': 'だけど', 'reading': 'だけど', 'romaji': 'dakedo',
                'zhMeaning': '但是', 'posZh': '连词', 'render': True,
                'showJlpt': False, 'reviewRequired': False,
            })
            index += 2
            did_change = True
        else:
            merged.append(cards[index])
            index += 1
    if did_change:
        frame['grammarCards'] = merged
        frame['caption']['furigana'] = [
            {'base': card['token'], 'reading': card['reading'], 'romaji': card['romaji']} for card in merged
        ]
        frame['caption']['romaji'] = ' '.join(card['romaji'] for card in merged)
        frame['analysisStatus'] = 'global-connective-normalized'
        changed.append(frame['id'])

PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Merged だけど in:', ', '.join(changed) if changed else 'none')
