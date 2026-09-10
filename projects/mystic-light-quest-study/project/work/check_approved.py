import hashlib
import json
import sys
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]; P=ROOT/'project'
sys.path.insert(0,str(P/'render'))
from render_video import ForegroundRenderer
from foreground_layout import plan,qrc_spans
from verify_render_gate import verify_review_gate
verify_review_gate(ROOT)
v=ForegroundRenderer(ROOT,1920,1080); draw=ImageDraw.Draw(Image.new('RGBA',(1920,1080)))
rows=[]; repeats={}
for fid,f in v.frames.items():
    v.render(fid,None,P/f'qa/approved-frames/{fid}.png')
    layout=v.last_layout
    boxes=[]; roman=[]
    for ruby in layout['rubies']:
        x=layout['xs'][ruby['start']]
        boxes.append((x-2,x+draw.textlength(ruby['reading'],font=v.font(28))+2))
    for b in layout['blocks']:
        if b['sourceWidth']: boxes.append((b['sourceX']-2,b['sourceX']+b['sourceWidth']+2))
        if b['romajiWidth']: roman.append((b['romajiX']-2,b['romajiX']+b['romajiWidth']+2))
    for row in (boxes,roman):
        row.sort(); assert all(a[1]<=b[0] for a,b in zip(row,row[1:])),fid
    for r in layout['rubies']:
        a,b=layout['spans'][r['cardIndex']]
        assert a+r['surfaceOffset']==r['start']
        assert r['end']<=b
    jp=f['caption']['japanese']
    if jp in repeats: assert repeats[jp]==f['grammarCards']
    repeats[jp]=f['grammarCards']
    rows.append({'frameId':fid,'cards':len(f['grammarCards']),'width':layout['width'],'annotationCollisions':0,'romajiCollisions':0})
for fid,active in [('l018',4),('l025',2)]:
    v.render(fid,active,P/f'qa/approved-frames/{fid}-highlight.png')
    plain=Image.open(P/f'qa/approved-frames/{fid}.png'); highlighted=Image.open(P/f'qa/approved-frames/{fid}-highlight.png')
    assert plain.crop((0,600,1920,1080)).tobytes()==highlighted.crop((0,600,1920,1080)).tobytes()
assert v.frames['l018']['grammarCards'][1]['reading']=='ゆける'
assert v.frames['l025']['grammarCards'][0]['token']=='心が躍れば'
assert sum(len(f['grammarCards']) for f in v.frames.values())==136
report={'schemaVersion':2,'status':'mechanical-passed','scope':'approved-static-layout','frameSha256':hashlib.sha256((P/'frames.json').read_bytes()).hexdigest(),'frameCount':42,'cardCount':136,'results':rows,'visualStatus':'pending','renderAuthorized':False}
(P/'qa/approved-layout-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: review gate, 42 approved static layouts, 136 cards, ruby anchors, no collisions, repeated cards consistent, non-highlighting cards.')
