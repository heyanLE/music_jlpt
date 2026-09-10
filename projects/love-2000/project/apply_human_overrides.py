import json
from pathlib import Path
root=Path(__file__).parent
data=json.loads((root/'love2000.frames.approved.json').read_text(encoding='utf-8'))
overrides=json.loads((root/'human-overrides.json').read_text(encoding='utf-8'))
for frame in data['frames']:
    override=overrides.get(frame['id'])
    if not override: continue
    cards=[]
    for card in override['grammarCards']:
        card={**card,'render':True,'showJlpt':False,'reviewRequired':False}
        cards.append(card)
    frame['grammarCards']=cards
    frame['caption']['furigana']=[{'base':c['token'],'reading':c['reading'],'romaji':c['romaji']} for c in cards]
    frame['analysisStatus']='human-override-applied'
data['humanOverridesApplied']=sorted(overrides)
(root/'love2000.frames.approved.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
