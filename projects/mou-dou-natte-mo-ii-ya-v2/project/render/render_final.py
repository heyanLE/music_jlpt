"""Template-driven final renderer for the approved Mou v2 frames."""
from __future__ import annotations
import hashlib, json, math, re, subprocess, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT=Path(__file__).resolve().parents[1]; ROOT=PROJECT.parent; SRC=ROOT/'source'; WORK=PROJECT/'work'/'20260815-r01'; FINAL=ROOT/'deliverables'/'final'
W,H,FPS=1920,1080,30; FONT='C:/Windows/Fonts/msyhbd.ttc'; DURATION=203.102
def js(p): return json.loads(p.read_text(encoding='utf8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
frames=js(PROJECT/'frames.json')['frames']; manifest=js(PROJECT/'input-manifest.json'); fg=js(PROJECT/'templates'/'foreground.json'); bg=js(PROJECT/'templates'/'background.json'); layout=js(PROJECT/'render'/'resolved-layout.json'); palette=layout['palette']
def color(hexv, alpha=255):
    h=hexv.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))+(alpha,)
ACCENT=color(palette['accent'])
# The accent is a dark magic purple.  Lift its lightness and saturation for a
# high-contrast active state that remains legible through the lyric veil.
ACTIVE=(111,169,255,255)
BODY=(255,255,255,245); CARD=color(palette['accent'],191)
def font(n): return ImageFont.truetype(FONT,n)
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if not c.isspace())
def latin_at(s,i): return s[i].isascii() and (s[i].isalpha() or s[i].isdigit() or s[i] in "'-")
def units(frame, draw):
    text=frame['caption']['japanese']; cards=frame['grammarCards']; out=[]; pos=ci=0
    while pos<len(text):
        if ci<len(cards) and text.startswith(cards[ci]['token'],pos):
            token=cards[ci]['token']; out.append(('card',ci,token,font(70),pos,pos+len(token))); pos+=len(token);ci+=1;continue
        if latin_at(text,pos):
            e=pos+1
            while e<len(text) and latin_at(text,e): e+=1
            out.append(('raw',None,text[pos:e],font(42),pos,e));pos=e;continue
        out.append(('raw',None,text[pos],font(70),pos,pos+1));pos+=1
    # all source chars are kept in display order, including punctuation and English.
    return [u+(draw.textbbox((0,0),u[2],font=u[3])[2],) for u in out]
def wrap(draw,text,ft,maxw,maxlines=2):
    ls=[];cur=''
    for ch in text:
        if cur and draw.textbbox((0,0),cur+ch,font=ft)[2]>maxw: ls.append(cur);cur=ch
        else: cur+=ch
        if len(ls)>=maxlines: break
    if cur and len(ls)<maxlines:ls.append(cur)
    return ls or ['']
def fit_single(draw,text,start,maxw,minimum=12):
    """Keep each card field on one line by shrinking, never wrapping."""
    for size in range(start, minimum-1, -1):
        ft=font(size)
        if draw.textbbox((0,0),text,font=ft)[2] <= maxw:
            return ft
    return font(minimum)
def fg_text(draw, xy, text, ft, fill, stroke=3):
    """Foreground typography only; learning cards intentionally remain clean."""
    draw.text(xy, text, font=ft, fill=fill, stroke_width=stroke, stroke_fill=(0,0,0,230))
def active_for(frame):
    # qrc parts already came from the frozen QM decode, so no fuzzy re-indexing.
    parts=[]; cursor=0; target=norm(frame['caption']['japanese'])
    for part in frame['displayUnits'][0].get('qrcParts',[]):
        tx=norm(part['text']); a=cursor; cursor+=len(tx)
        if tx: parts.append((part['startMs'],part['startMs']+part['durationMs'],a,cursor))
    return parts,target
def render(frame, active_index, path):
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im,'RGBA')
    # lyric-only veil and all foreground components live in one alpha frame.
    d.rectangle((0,0,W,H),fill=(0,0,0,71))
    cover=Image.open(SRC/'cover.jpg').convert('RGBA').resize((220,220),Image.Resampling.LANCZOS); im.alpha_composite(cover,(850,35))
    us=units(frame,d); gap=18; total=sum(x[-1] for x in us)+gap*(len(us)-1); x=(W-total)/2
    target=norm(frame['caption']['japanese']); active_char=None
    if active_index is not None:
        _,_,a,b=active_for(frame)[0][active_index]; active_char=(a,b)
    character_cursor=0
    override_reading=frame['caption'].get('readingOverride')
    if override_reading:
        b=d.textbbox((0,0),override_reading,font=font(28)); fg_text(d,((W-b[2])/2,320),override_reading,font(28),BODY,2)
        override_roma=frame['caption'].get('romajiOverride',''); b=d.textbbox((0,0),override_roma,font=font(34)); fg_text(d,((W-b[2])/2,485),override_roma,font(34),BODY)
    for kind,ci,text,ft,start,end,wid in us:
        lo=len(norm(frame['caption']['japanese'][:start])); hi=len(norm(frame['caption']['japanese'][:end]))
        hit=active_char is not None and lo<active_char[1] and hi>active_char[0]
        fill=ACTIVE if hit else BODY
        if kind=='card':
            c=frame['grammarCards'][ci]
            # annotations from reviewed records: kanji-only / loanword source.
            ann=[a for a in frame['caption'].get('annotationRuns',[]) if a.get('base') and a['base'] in text]
            if c.get('sourceWord'):
                s=c['sourceWord']; b=d.textbbox((0,0),s,font=font(23)); fg_text(d,(x+(wid-b[2])/2,320),s,font(23),fill,2)
            else:
                # A reviewed token can contain several kanji runs, including
                # runs after literal kana (e.g. この世, 取り繕う).  Position
                # each reading over its measured kanji-run anchor.
                for note in ann:
                    s=note.get('reading','')
                    prefix=text[:text.index(note['base'])]
                    offset=d.textbbox((0,0),prefix,font=ft)[2]
                    fg_text(d,(x+offset,320),s,font(28),fill,2)
            fg_text(d,(x,360),text,ft,fill)
            if not override_reading:
                roma=c['romaji']; b=d.textbbox((0,0),roma,font=font(34)); fg_text(d,(x+(wid-b[2])/2,485),roma,font(34),fill)
        else: fg_text(d,(x,382 if ft.size==42 else 360),text,ft,fill)
        x+=wid+gap
    trans=frame['caption'].get('translationZh',''); lines=wrap(d,trans,font(45),1650)
    for i,line in enumerate(lines):
        b=d.textbbox((0,0),line,font=font(45));fg_text(d,((W-b[2])/2,595+i*50),line,font(45),BODY)
    cards=frame['grammarCards']
    if not cards:
        im.save(path); return
    # All cards stay in one horizontal row.  A dense lyric line scales card
    # text down to fit rather than creating a second row or wrapping text.
    cols=len(cards); cw=(1740-(cols-1)*12)/cols; ch=245
    for i,c in enumerate(cards):
        col=i;left=90+col*(cw+12);top=705; right=left+cw
        d.rounded_rectangle((left,top,right,top+ch),radius=20,fill=CARD,outline=ACTIVE[:3]+(145,),width=2)
        token=c['token']; tf=fit_single(d,token,37,cw-24,14); b=d.textbbox((0,0),token,font=tf);d.text((left+(cw-b[2])/2,top+25),token,font=tf,fill=BODY)
        meaning=c.get('functionZh',c.get('zhMeaning','')); mf=fit_single(d,meaning,26,cw-24,11); b=d.textbbox((0,0),meaning,font=mf);d.text((left+(cw-b[2])/2,top+90),meaning,font=mf,fill=BODY)
        p=c['posZh'];pf=fit_single(d,p,25,cw-24,11);b=d.textbbox((0,0),p,font=pf);d.text((left+(cw-b[2])/2,top+150),p,font=pf,fill=BODY)
    im.save(path)
def main():
    WORK.mkdir(parents=True,exist_ok=True); FINAL.mkdir(parents=True,exist_ok=True)
    # User-authorized render snapshot.
    auth={'userWording':'按当前审核版渲染','createdAt':datetime.now(timezone.utc).isoformat(),'frameSha256':sha(PROJECT/'frames.json'),'templateSha256':sha(PROJECT/'templates'/'foreground.json'),'backgroundTemplateSha256':sha(PROJECT/'templates'/'background.json'),'sourceSha256':{p.name:sha(p) for p in [SRC/'background.mp4',SRC/'music.mp3',SRC/'cover.jpg']}}
    dump(PROJECT/'render'/'render-authorization.json',auth)
    dump(PROJECT/'render'/'render-plan.json',{'runId':'20260815-r01','canvas':[W,H],'fps':FPS,'clock':'audio','offsetMs':0,'foregroundVisibility':'lyric-only','sourceHashes':auth,'output':str(FINAL/'mou-dou-natte-mo-ii-ya-v2--study-current-v2--20260815-r01.mp4')})
    concat=[];idx=0
    # transparent gaps: no cover, cards, text, or veil outside lyric frames.
    blank=WORK/'blank.png';Image.new('RGBA',(W,H),(0,0,0,0)).save(blank)
    cursor=0
    for fr in frames:
        if cursor<fr['startMs']:
            concat += [f"file '{blank.as_posix()}'",f'duration {(fr["startMs"]-cursor)/1000:.3f}']
        events, _=active_for(fr); local=fr['startMs']
        for event_i,(s,e,_,_) in enumerate(events):
            s=max(s,fr['startMs']);e=min(e,fr['endMs'])
            if local<s: 
                p=WORK/f'{idx:04d}.png';render(fr,None,p);concat += [f"file '{p.as_posix()}'",f'duration {(s-local)/1000:.3f}'];idx+=1
            if e>s:
                p=WORK/f'{idx:04d}.png';render(fr,event_i,p);concat += [f"file '{p.as_posix()}'",f'duration {(e-s)/1000:.3f}'];idx+=1
            local=max(local,e)
        if local<fr['endMs']:
            p=WORK/f'{idx:04d}.png';render(fr,None,p);concat += [f"file '{p.as_posix()}'",f"duration {(fr['endMs']-local)/1000:.3f}"];idx+=1
        cursor=max(cursor,fr['endMs'])
    if cursor<int(DURATION*1000): concat += [f"file '{blank.as_posix()}'",f'duration {DURATION-cursor/1000:.3f}']
    concat += [f"file '{blank.as_posix()}'"]
    cfile=WORK/'foreground.concat.txt';cfile.write_text('\n'.join(concat),encoding='utf8')
    out=FINAL/'mou-dou-natte-mo-ii-ya-v2--study-current-v2--20260815-r01.mp4'
    vf='[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,fps=30[bg];[1:v]fps=30,format=rgba[fg];[bg][fg]overlay=0:0:format=auto,fps=30,format=yuv420p[v]'
    subprocess.run(['ffmpeg','-y','-v','error','-stream_loop','-1','-i',str(SRC/'background.mp4'),'-f','concat','-safe','0','-i',str(cfile),'-i',str(SRC/'music.mp3'),'-filter_complex',vf,'-map','[v]','-map','2:a:0','-t',f'{DURATION:.3f}','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r','30','-fps_mode','cfr','-c:a','aac','-b:a','320k','-movflags','+faststart',str(out)],check=True)
    print(out)
if __name__=='__main__': main()
