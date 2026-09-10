"""Propagate human-reviewed cards to identical later lyric lines and create review copy."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).parent
APPROVED = ROOT / 'love2000.frames.approved.json'
OUT = ROOT / 'output' / 'love2000-remaining-review.md'

def stamp(ms):
    return f'{ms // 60000:02d}:{(ms % 60000) // 1000:02d}.{ms % 1000:03d}'

data = json.loads(APPROVED.read_text(encoding='utf-8'))
# The rendering JSON is rebuilt from rules and does not retain this field.
# Keep the original review manifest as the durable authority.
review_manifest = json.loads((ROOT / 'love2000.frames.review.json').read_text(encoding='utf-8'))
reviewed = set(review_manifest.get('reviewedFrameIds', []))
reviewed.update(data.get('humanReviewedFrameIds', []))
overrides = json.loads((ROOT / 'human-overrides.json').read_text(encoding='utf-8'))
reviewed.update(overrides.keys())
frames = {frame['id']: frame for frame in data['frames']}

# A reviewed line is canonical for any later line with exactly the same displayed lyric.
canonical_by_text = {}
for frame_id in reviewed:
    frame = frames.get(frame_id)
    if frame and frame.get('kind') == 'lyric':
        canonical_by_text[frame['caption']['japanese']] = frame

synced = []
for frame in data['frames']:
    if frame.get('kind') != 'lyric' or frame['id'] in reviewed:
        continue
    canonical = canonical_by_text.get(frame['caption']['japanese'])
    if not canonical:
        continue
    frame['grammarCards'] = copy.deepcopy(canonical['grammarCards'])
    frame['caption']['furigana'] = copy.deepcopy(canonical['caption']['furigana'])
    frame['caption']['romaji'] = canonical['caption']['romaji']
    frame['analysisStatus'] = f'inherited-from-reviewed-{canonical["id"]}'
    frame['reviewRequired'] = False
    synced.append((frame['id'], canonical['id'], frame['caption']['japanese']))

data['reviewStatus'] = 'reviewed-cards-synced; remaining-lines-await-human-review'
data['syncedReviewedCards'] = [
    {'frameId': target, 'sourceFrameId': source, 'japanese': text}
    for target, source, text in synced
]
APPROVED.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

lines = [
    '# LOVE 2000｜剩余词卡审核',
    '',
    '已以人工审核内容为基准同步重复歌词；下方只保留仍需确认的句子。助词的“功能”不是字面词义。',
    '',
    '## 已同步的重复句',
    '',
]
for target, source, text in synced:
    lines.append(f'- `{target}` ← `{source}`：{text}')
lines.append('')

skipped = reviewed | {target for target, _, _ in synced}
for frame in data['frames']:
    if frame.get('kind') != 'lyric' or frame['id'] in skipped:
        continue
    caption = frame['caption']
    lines += [
        f'## {frame["id"]} · {stamp(frame["startMs"])}',
        '',
        f'日文：{caption["japanese"]}',
        f'暂定中文：{caption["translationZh"]}',
        '',
        '待核词卡：',
    ]
    for card in frame['grammarCards']:
        meaning = card.get('functionZh') or card['zhMeaning']
        lines += [
            f'- `{card["token"]}`｜{card["reading"]}｜{card["romaji"]}',
            f'  - 暂定：{meaning}',
            f'  - 词性：{card["posZh"]}',
        ]
    lines.append('')
OUT.write_text('\n'.join(lines), encoding='utf-8')

print(f'Synced {len(synced)} repeated lyric frames.')
print(OUT)
