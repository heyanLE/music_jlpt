import json, re
from pathlib import Path
root=Path(__file__).parent
text=(root/'output'/'love2000-qmts.xml').read_text(encoding='utf-8')
items=[]
for mm,ss,content in re.findall(r'^\[(\d{2}):(\d{2}\.\d{2})\](.*)$',text,re.M):
    if not content or content.startswith('//') or content.startswith('TME'): continue
    items.append((int(mm)*60000+round(float(ss)*1000),content.strip()))
data=json.loads((root/'love2000.frames.approved.json').read_text(encoding='utf-8'))
for frame in data['frames']:
    if frame['kind']!='lyric': continue
    parts=[value for start,value in items if frame['startMs']-80 <= start < frame['endMs']-80]
    if parts: frame['caption']['translationZh']='，'.join(parts)
data['translationSource']='QQ Music qmts.qrc decoded locally'
(root/'love2000.frames.approved.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
