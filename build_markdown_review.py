import json
from pathlib import Path

root = Path(__file__).parent
data = json.loads((root / 'love2000.frames.annotated.review.json').read_text(encoding='utf-8'))
reviewed = set(json.loads((root / 'love2000.frames.review.json').read_text(encoding='utf-8')).get('reviewedFrameIds', []))
lines = ['# LOVE 2000｜剩余逐句词卡审核清单', '', '范围：l011 起，已确认的 l001–l010 已排除。助词的“中文”栏为功能，不是词义。', '']
for frame in data['frames']:
    if frame['kind'] != 'lyric' or frame['id'] in reviewed:
        continue
    cap = frame['caption']
    lines += [f"## {frame['id']} · {frame['startMs']/1000:.3f}s", '', f"**日文**：{cap['japanese']}  ", f"**罗马音**：{cap['romaji']}  ", f"**暂定中文**：{cap['translationZh']}", '', '| 分词 | 假名 | 罗马音 | 当前中文 / 助词功能 | 词性 |', '|---|---|---|---|---|']
    for c in frame['grammarCards']:
        meaning = c.get('functionZh') or c['zhMeaning']
        lines.append(f"| {c['token']} | {c['reading']} | {c['romaji']} | {meaning} | {c['posZh']} |")
    lines.append('')
(root / 'output' / 'love2000-remaining-review.md').write_text('\n'.join(lines), encoding='utf-8')
