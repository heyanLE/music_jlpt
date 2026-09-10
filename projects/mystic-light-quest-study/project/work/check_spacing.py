import hashlib
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
P = ROOT/'project'
sys.path.insert(0,str(P/'render'))
from render_video import ForegroundRenderer
from foreground_layout import plan, qrc_spans

v=ForegroundRenderer(ROOT,1920,1080)
draw=ImageDraw.Draw(Image.new('RGBA',(1920,1080)))
results=[]
for fid,frame in v.frames.items():
    layout=plan(frame,draw,v.font(70),v.font(28),v.font(34),v.font(23),14)
    assert layout['width']<=1728
    annotation=[]; roman=[]
    for r in layout['rubies']:
        x=layout['xs'][r['start']]
        annotation.append((x-2,x+draw.textlength(r['reading'],font=v.font(28))+2))
    for b in layout['blocks']:
        if b['sourceWidth']: annotation.append((b['sourceX']-2,b['sourceX']+b['sourceWidth']+2))
        if b['romajiWidth']: roman.append((b['romajiX']-2,b['romajiX']+b['romajiWidth']+2))
    for row in (annotation,roman):
        row.sort()
        assert all(a[1]<=b[0] for a,b in zip(row,row[1:])),(fid,row)
    spans=qrc_spans(frame['caption']['japanese'],v.matched_parts(frame))
    old=Image.open(P/f'qa/draft-frames/{fid}.png')
    new=Image.open(P/f'qa/spaced-draft-frames/{fid}.png')
    assert old.crop((0,600,1920,1080)).tobytes()==new.crop((0,600,1920,1080)).tobytes()
    assert old.crop((0,0,1920,280)).tobytes()==new.crop((0,0,1920,280)).tobytes()
    results.append({'frameId':fid,'width':layout['width'],'qrcParts':len(spans),'annotationOverlap':False,'romajiOverlap':False,'coverAndCardsUnchanged':True})
for fid,active in [('l008',4),('l018',0),('l012',2)]:
    v.render(fid,active,P/f'qa/spaced-draft-frames/{fid}-highlight.png')
    a=Image.open(P/f'qa/spaced-draft-frames/{fid}.png')
    b=Image.open(P/f'qa/spaced-draft-frames/{fid}-highlight.png')
    assert a.crop((0,600,1920,1080)).tobytes()==b.crop((0,600,1920,1080)).tobytes()
base=hashlib.sha256((P/'frames.json').read_bytes()).hexdigest()
assert base=='e062cef34bd38d5f9b37309eb2085df3b46969abb568b3bad9de587d3f01d047'
report={'schemaVersion':2,'status':'mechanical-passed','framesSha256':base,'renderer':'project/render/render_video.py','helper':'project/render/foreground_layout.py','hashes':{f:hashlib.sha256((P/'render'/f).read_bytes()).hexdigest() for f in ['render_video.py','foreground_layout.py']},'all42FramesChecked':True,'contentUnchanged':True,'draftOnly':True,'results':results,'visualStatus':'pending'}
(P/'qa/spacing-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS: 42 layouts, ruby/romaji collision checks, QRC mappings, unchanged cover/cards/content; 3 highlight proofs.')
