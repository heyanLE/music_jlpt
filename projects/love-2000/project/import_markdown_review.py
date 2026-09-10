import json, re
from pathlib import Path

root=Path(__file__).parent
md=(root/'output'/'love2000-review.md').read_text(encoding='utf-8')
data=json.loads((root/'love2000.frames.approved.json').read_text(encoding='utf-8'))
sections=re.split(r'^## (l\d+) .*$', md, flags=re.M)
updates={}
for i in range(1,len(sections),2):
    frame_id, body=sections[i], sections[i+1]
    translation=re.search(r'\*\*暂定中文\*\*：(.+)',body)
    rows=[]
    for line in body.splitlines():
        if not line.startswith('|') or line.startswith('|---') or '分词' in line: continue
        cells=[x.strip() for x in line.strip('|').split('|')]
        if len(cells)==5: rows.append(cells)
    updates[frame_id]={'translation':translation.group(1).strip() if translation else None,'rows':rows}
for frame in data['frames']:
    change=updates.get(frame['id'])
    if not change: continue
    if change['translation']: frame['caption']['translationZh']=change['translation']
    cards=[]
    for token,reading,romaji,meaning,pos in change['rows']:
        card={'token':token,'reading':reading,'romaji':romaji,'zhMeaning':meaning,'posZh':pos,'render':True,'showJlpt':False,'reviewRequired':False}
        if '助词' in pos: card['functionZh']=meaning
        cards.append(card)
    if cards:
        frame['grammarCards']=cards
        frame['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in cards]
        frame['analysisStatus']='human-markdown-review-imported'
data['reviewStatus']='human-markdown-review-imported'
(root/'love2000.frames.approved.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
