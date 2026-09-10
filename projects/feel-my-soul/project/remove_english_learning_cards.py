"""English lyric text is displayed as-is, without Japanese study annotations."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).parent
PATH=ROOT/'feel-my-soul.frames.approved.json'
REVIEW=ROOT/'output'/'feel-my-soul-review.md'
data=json.loads(PATH.read_text(encoding='utf8'))

def english_only(text):
    return bool(re.fullmatch(r"[A-Za-z0-9'’ .!?,\-]+", text.strip()))

changed=[]
for frame in data['frames']:
    cards=frame['grammarCards']
    kept=[card for card in cards if not english_only(card['token'])]
    if len(kept)==len(cards):
        continue
    frame['grammarCards']=kept
    frame['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in kept]
    frame['caption']['romaji']=' '.join(c['romaji'] for c in kept)
    frame['analysisStatus']='english-learning-cards-removed'
    changed.append(frame['id'])

data['englishDisplayRule']='English lyric text displays without furigana, romaji, or grammar cards.'
PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

lines=['# feel my soul｜智能补全后词卡审核','', '规则：英语歌词只显示原文，不显示假名、罗马音或词卡；日文部分保留学习标注。','']
for f in data['frames']:
    cap=f['caption']; lines += [f'## {f["id"]} · {f["startMs"]/1000:.3f}s','',f'日文：{cap["japanese"]}',f'暂定中文：{cap["translationZh"]}','']
    if not f['grammarCards']:
        lines += ['词卡：本句为英语歌词，不渲染词卡。','']
        continue
    lines.append('词卡：')
    for c in f['grammarCards']:
        lines += [f'- `{c["token"]}`｜{c["reading"]}｜{c["romaji"]}',f'  - 暂定：{c.get("functionZh") or c["zhMeaning"]}',f'  - 词性：{c["posZh"]}']
    lines.append('')
REVIEW.write_text('\n'.join(lines),encoding='utf8')
print('English annotations removed from:',', '.join(changed))
