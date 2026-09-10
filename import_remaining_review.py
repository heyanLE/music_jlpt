"""Persist only the sections the user changed in the plain-language review file."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
APPROVED = ROOT / 'love2000.frames.approved.json'
REVIEW = ROOT / 'output' / 'love2000-remaining-review.md'

data = json.loads(APPROVED.read_text(encoding='utf-8'))
finalize_all = '--all-reviewed' in sys.argv
frames = {frame['id']: frame for frame in data['frames']}
updates, current, card = {}, None, None

for raw in REVIEW.read_text(encoding='utf-8').splitlines():
    header = re.match(r'^## (l\d+) · ', raw)
    if header:
        current = header.group(1)
        updates[current] = {'translation': None, 'cards': []}
        card = None
        continue
    if not current:
        continue
    if raw.startswith('暂定中文：'):
        updates[current]['translation'] = raw.removeprefix('暂定中文：').strip()
        continue
    match = re.match(r'^- `(.+)`｜([^｜]+)｜(.+)$', raw)
    if match:
        card = {'token': match.group(1), 'reading': match.group(2), 'romaji': match.group(3)}
        updates[current]['cards'].append(card)
        continue
    if card and raw.startswith('  - 暂定：'):
        card['zhMeaning'] = raw.removeprefix('  - 暂定：').strip()
    elif card and raw.startswith('  - 词性：'):
        card['posZh'] = raw.removeprefix('  - 词性：').strip()

changed = []
for frame_id, update in updates.items():
    frame = frames.get(frame_id)
    if not frame or not update['cards']:
        continue
    proposed_cards = []
    valid = all({'token', 'reading', 'romaji', 'zhMeaning', 'posZh'} <= set(card) for card in update['cards'])
    if not valid:
        continue
    for card in update['cards']:
        card = dict(card)
        card.update({'render': True, 'showJlpt': False, 'reviewRequired': False})
        if '助' in card['posZh']:
            card['functionZh'] = card['zhMeaning']
        proposed_cards.append(card)
    existing = [(c['token'], c['reading'], c['romaji'], c.get('functionZh') or c['zhMeaning'], c['posZh']) for c in frame['grammarCards']]
    proposed = [(c['token'], c['reading'], c['romaji'], c['zhMeaning'], c['posZh']) for c in proposed_cards]
    translation_changed = update['translation'] and update['translation'] != frame['caption']['translationZh']
    if existing == proposed and not translation_changed and not finalize_all:
        continue
    frame['grammarCards'] = proposed_cards
    frame['caption']['furigana'] = [
        {'base': c['token'], 'reading': c['reading'], 'romaji': c['romaji']} for c in proposed_cards
    ]
    frame['caption']['romaji'] = ' '.join(c['romaji'] for c in proposed_cards)
    if update['translation']:
        frame['caption']['translationZh'] = update['translation']
    frame['analysisStatus'] = 'human-final-review-imported' if finalize_all else 'human-remaining-review-imported'
    frame['reviewRequired'] = False
    changed.append(frame_id)

human_reviewed = set(data.get('humanReviewedFrameIds', []))
human_reviewed.update(changed)
data['humanReviewedFrameIds'] = sorted(human_reviewed)
APPROVED.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
label = 'Imported final reviewed sections' if finalize_all else 'Imported changed sections'
print(label + ':', ', '.join(changed) if changed else 'none')
