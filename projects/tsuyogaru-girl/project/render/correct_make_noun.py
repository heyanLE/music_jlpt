from pathlib import Path
import json

root=Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
frames=root/'project'/'frames.json'
data=json.loads(frames.read_text(encoding='utf-8'))
for frame in data['frames']:
    if frame['id'] in {'l001','l068','l069'}:
        card=next(card for card in frame['grammarCards'] if card['token']=='負け')
        card['zhMeaning']='失败'
        card['posZh']='名词'
        card['fieldProvenance']='user-correction-20260817'
frames.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
json.loads(frames.read_text(encoding='utf-8'))
