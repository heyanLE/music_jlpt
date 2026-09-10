import hashlib,json,re,sys
from pathlib import Path
from PIL import Image,ImageChops
R=Path(__file__).resolve().parents[2];P=R/'project'
sys.path.insert(0,str(P/'render'))
from render_video import ForegroundRenderer
from foreground_layout import qrc_spans
v=ForegroundRenderer(R,1920,1080);Q=P/'qa/character-highlight';Q.mkdir(exist_ok=True)
units=0
for f in v.frames.values():
    parts=v.matched_parts(f);spans=qrc_spans(f['caption']['japanese'],parts)
    for p,(a,b) in zip(parts,spans):
        if re.search(r'[一-鿿ぁ-ゖァ-ヺ]',p['text']):
            assert len(p['text'].strip())==b-a==1
            units+=1
samples=[]
for fid,active in [('l001',0),('l001',1),('l018',4),('l025',2),('l012',2)]:
    outputs=[]
    for mode in ['token','character']:
        v.presentation['highlight']['japaneseMode']=mode
        path=Q/f'{fid}-{active}-{mode}.png';v.render(fid,active,path);outputs.append(path)
    a,b=[Image.open(p) for p in outputs]
    assert a.crop((0,0,1920,330)).tobytes()==b.crop((0,0,1920,330)).tobytes()
    assert a.crop((0,420,1920,1080)).tobytes()==b.crop((0,420,1920,1080)).tobytes()
    if fid=='l012':assert a.tobytes()==b.tobytes()
    else:assert ImageChops.difference(a.convert('RGB'),b.convert('RGB')).getbbox()
    samples.append({'frameId':fid,'partIndex':active,'newImage':outputs[1].relative_to(R).as_posix()})
sha=hashlib.sha256((P/'frames.json').read_bytes()).hexdigest()
assert sha=='6f02999db4cfc57334b9951ca9f5be4b4ac2123362907581563c6c439b7e5c9d'
report={'schemaVersion':1,'result':'mechanical-passed','japaneseTimedCharacters':units,'allFramesMapped':42,'framesSha256':sha,'outsideJapaneseRowPixelIdentical':True,'englishPixelIdentical':True,'samples':samples,'visualStatus':'pending','finalRenderAuthorized':False}
(Q/'qa-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'japaneseTimedCharacters':units,'samples':len(samples),'otherRowsUnchanged':True}))
