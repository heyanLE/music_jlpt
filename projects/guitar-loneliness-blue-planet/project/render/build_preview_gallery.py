"""Compose review PNGs from actual source backgrounds, never a final video."""
import hashlib
import html
import io
import json
import subprocess
from pathlib import Path
from PIL import Image,ImageFilter,ImageEnhance
from foreground_renderer import ForegroundRenderer

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'project'
FFMPEG='C:/Users/eke_l/miniconda3/envs/manim_render312/Library/bin/ffmpeg.exe'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    frames=load(P/'review/frames-proposed.json')['frames']
    r=ForegroundRenderer(ROOT,1920,1080); r.frames={f['id']:f for f in frames};r.ordered_ids=list(r.frames)
    out=ROOT/'deliverables/review/frames-r2';out.mkdir(exist_ok=True)
    cover=Image.open(ROOT/'source/cover.jpg').convert('RGB').resize((1920,1920),Image.Resampling.LANCZOS).crop((0,420,1920,1500)).filter(ImageFilter.GaussianBlur(30))
    cover=ImageEnhance.Brightness(cover).enhance(.75).convert('RGBA')
    records=[]
    for f in frames:
        t=f['startMs']/1000+20.877+.15
        if t<126.74:
            raw=subprocess.run([FFMPEG,'-v','error','-ss',str(t+16),'-i',str(ROOT/'source/background.mp4'),'-frames:v','1','-vf','scale=-2:1080,crop=1920:1080','-f','image2pipe','-c:v','png','-'],capture_output=True,check=True).stdout
            bg=Image.open(io.BytesIO(raw)).convert('RGBA')
        else:bg=cover.copy()
        parts=r.matched_parts(f)
        ai=next((i for i,part in enumerate(parts) if part.get('startMs',0)<=round((t-20.877)*1000)<part.get('endMs',0)),0)
        layer=r.render(f['id'],ai,None)
        bg.alpha_composite(layer);bg.convert('RGB').save(out/f"{f['id']}.png")
        thumb=bg.convert('RGB');thumb.thumbnail((640,360));thumb.save(out/f"{f['id']}-thumb.jpg",quality=85)
        layout=r.measured_line(f)
        assert all(a['right']<=b['left'] for a,b in zip(layout['boxes'],layout['boxes'][1:])),f['id']
        assert all(layout['positions'][i]<=layout['positions'][i+1] for i in range(len(layout['positions'])-1)),f['id']
        records.append({'id':f['id'],'outputTimeMs':round(t*1000),'background':'source-video' if t<126.74 else 'cover-gaussian','fontPx':layout['font'].size,'romajiFontPx':r.font(34).size,'lyricWidth':layout['width'],'sharedAnchorsNonOverlapping':True})
    # Check countdown appearance without inserting or shifting audio.
    for value in (3,2,1):
        r.render('l001',None,out/f'countdown-{value}.png',countdown_value=value)
    sections=[]
    for f in frames:
        fid=f['id'];jp=html.escape(f['caption']['japanese']);zh=html.escape(f['caption'].get('translationZh',''))
        sections.append(f'<article><h2>{fid} · {jp}</h2><a href="frames-r2/{fid}.png" target="_blank"><img src="frames-r2/{fid}-thumb.jpg" loading="lazy"></a><p>{zh}</p></article>')
    page='<!doctype html><meta charset="utf-8"><title>词卡静态审核 R2</title><style>body{background:#19151a;color:#faf5f8;font:17px system-ui;margin:28px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:20px}article{background:#282128;padding:16px;border-radius:12px}img{width:100%}h2{font-size:18px}a{color:#ff72ad}</style><h1>吉他与孤独与蓝色星球 · 静态审核 R2</h1><p>48句；最新简短释义与动词标签。点击图片查看1920×1080原图。原声/歌曲时间轴未改；此页面不是最终视频，也未展示频谱动画。</p><main>'+''.join(sections)+'</main>'
    (ROOT/'deliverables/review/静态预览-r2.html').write_text(page,encoding='utf-8')
    report={'status':'passed-static-only','proposedFramesSha256':hashlib.sha256((P/'review/frames-proposed.json').read_bytes()).hexdigest(),'rendererSha256':hashlib.sha256(Path(__file__).with_name('foreground_renderer.py').read_bytes()).hexdigest(),'frames':records,'spectrumIncluded':False,'countdownValuesChecked':[3,2,1],'notFinalQa':True}
    (P/'qa/shared-anchor-preview-r2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'gallery':str(ROOT/'deliverables/review/静态预览-r2.html'),'frames':len(records),'collisions':0},ensure_ascii=False))

if __name__=='__main__':main()
