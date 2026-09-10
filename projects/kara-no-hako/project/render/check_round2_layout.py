"""Check a proposal-only frame set without altering live content or rendering video."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw
from next_line_foreground import NextLineRenderer
from render_video import wrap

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('frames',type=Path); ap.add_argument('--stills',action='store_true'); args=ap.parse_args()
    baseline=sha(P/'frames.json'); doc=load(args.frames)
    renderer=NextLineRenderer(ROOT); renderer.frames={f['id']:f for f in doc['frames']}; renderer.ordered=sorted(doc['frames'],key=lambda f:f['startMs'])
    draw=ImageDraw.Draw(Image.new('RGBA',(1920,1080)))
    rows=[]; errors=[]
    out=P/'qa/round2-foreground'; out.mkdir(parents=True,exist_ok=True)
    for frame in renderer.ordered:
        cards=frame['grammarCards']; text=frame['caption']['japanese']; cursor=0
        assert re.sub(r'[\s？?!！、。]','',''.join(c['token'] for c in cards))==re.sub(r'[\s？?!！、。]','',text),frame['id']
        width=(1730-12*(len(cards)-1))//len(cards); inner=width-28
        lyric_font=renderer.fit(draw,text,70,53,1728); lyric_width=draw.textbbox((0,0),text,font=lyric_font)[2]; lyric_x=(1920-lyric_width)/2
        details=[]; roman_ranges=[]
        for c in cards:
            assert bool(c.get('zhMeaning')) != bool(c.get('functionZh')),(frame['id'],c['token'])
            assert not any(c.get(k,'').startswith((':','：','含义：','词性：')) for k in ('zhMeaning','functionZh','grammarStructureZh'))
            start=text.find(c['token'],cursor); assert start>=cursor; cursor=start+len(c['token'])
            jp_x=lyric_x+draw.textbbox((0,0),text[:start],font=lyric_font)[2]; jp_width=draw.textbbox((0,0),c['token'],font=lyric_font)[2]
            rw=draw.textbbox((0,0),c['romaji'],font=renderer.font(34))[2]; rx=jp_x+(jp_width-rw)/2
            roman_ranges.append({'token':c['token'],'left':round(rx,2),'right':round(rx+rw,2)})
            meaning=c.get('functionZh',c.get('zhMeaning','')); wrapped=wrap(draw,meaning,renderer.font(26),inner)
            tf=renderer.fit(draw,c['token'],37,16,inner); gf=renderer.fit(draw,c['grammarStructureZh'],25,14,inner)
            details.append({'token':c['token'],'tokenFontSize':tf.size,'grammarFontSize':gf.size,'meaningLines':wrapped})
            if len(wrapped)>2: errors.append({'frameId':frame['id'],'token':c['token'],'issue':'meaning exceeds two lines'})
        overlaps=[{'leftToken':a['token'],'rightToken':b['token'],'overlapPx':round(a['right']-b['left'],2)} for a,b in zip(roman_ranges,roman_ranges[1:]) if a['right']>b['left']]
        # Actual glyphs may have padding; report every bounding-box collision rather than hiding it.
        rows.append({'frameId':frame['id'],'cards':len(cards),'cardWidthPx':width,'cardDetails':details,'romajiBoundingBoxOverlaps':overlaps})
        renderer.add_preview(Image.new('RGBA',(1920,1080)),frame)
        if args.stills: renderer.render(frame['id'],None,out/(frame['id']+'.png'))
    assert sha(P/'frames.json')==baseline
    report={'schemaVersion':1,'content':'unaccepted-proposal-only','framesSha256':sha(args.frames),'liveFramesUnchanged':True,'frameCount':len(rows),'cardCount':sum(r['cards'] for r in rows),'result':'needs-review' if errors else 'passed-mechanical','errors':errors,'rows':rows,'nextLineLayouts':renderer.preview_layouts,'visualReview':'pending'}
    (P/'qa/round2-layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'frames':len(rows),'cards':report['cardCount'],'romanCollisionFrames':[r['frameId'] for r in rows if r['romajiBoundingBoxOverlaps']],'errors':errors},ensure_ascii=False))

if __name__=='__main__': main()
