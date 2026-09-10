"""Render fresh QRC-timed foreground PNG states and compose lossless-audio MKV."""
from __future__ import annotations

import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
P, S = ROOT / "project", ROOT / "source"
RUN = P / "work" / "20260821-r02-line-hold"
OVER = RUN / "foreground"
W, H, FPS, DURATION = 1920, 1080, 30, 218533
FONT = "C:/Windows/Fonts/msyhbd.ttc"


def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def dump(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))
def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()
def norm(text: str): return "".join(unicodedata.normalize("NFKC", text).casefold().split())
def hx(value: str):
    value=value.lstrip("#"); return tuple(int(value[i:i+2],16) for i in (0,2,4))
def font(size): return ImageFont.truetype(FONT, size)
def outlined(draw, xy, text, fnt, fill, stroke): draw.text(xy, text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill="black")

def wrap(draw, text, fnt, max_w):
    result, line = [], ""
    for ch in text:
        if line and draw.textbbox((0,0),line+ch,font=fnt)[2] > max_w: result.append(line); line=ch
        else: line += ch
    if line: result.append(line)
    return result

def fit(draw, text, start, minimum, max_w):
    for size in range(start, minimum-1, -1):
        fnt=font(size)
        if draw.textbbox((0,0),text,font=fnt)[2] <= max_w: return fnt
    return font(minimum)

def card_anchor(draw, text, token, cursor, fnt):
    start = text.find(token, cursor)
    if start < 0: return None, cursor
    x = draw.textbbox((0,0),text[:start],font=fnt)[2]
    w = draw.textbbox((0,0),token,font=fnt)[2]
    return (x, w), start+len(token)

def render_state(frame, parts, active_index, palette, path):
    image=Image.new("RGBA",(W,H),(0,0,0,0))
    image.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,71)))
    cover=Image.open(S/"cover.jpg").convert("RGBA").resize((220,220),Image.Resampling.LANCZOS)
    image.alpha_composite(cover,(850,35)); draw=ImageDraw.Draw(image)
    text=frame["caption"]["japanese"]
    jf=fit(draw,text,70,53,int(W*.90)); tw=draw.textbbox((0,0),text,font=jf)[2]; x=(W-tw)/2
    active=hx(palette["activeTint"])+(255,); body=(255,255,255,242)
    # QRC parts retain exact mixed Japanese-English display order; only a matching part becomes active.
    for index, part in enumerate(parts):
        value=part["text"]; color=active if index==active_index else body
        outlined(draw,(x,330 if any(ord(c)>127 for c in text) else 352),value,jf,color,4)
        x += draw.textbbox((0,0),value,font=jf)[2]
    cards=frame["grammarCards"]
    # Card anchors are measured from the same lyric string; no annotations are made for literal kana.
    cursor=0; full_x=(W-tw)/2
    for card in cards:
        anchor,cursor=card_anchor(draw,text,card["token"],cursor,jf)
        if not anchor: continue
        px,pw=full_x+anchor[0],anchor[1]
        if card.get("sourceWord"):
            af=font(23); aw=draw.textbbox((0,0),card["sourceWord"],font=af)[2]
            outlined(draw,(px+(pw-aw)/2,295),card["sourceWord"],af,body,2)
        # Use stored kanji-only ruby entries that match the card surface.
        for ruby in frame["caption"].get("furigana",[]):
            base=ruby.get("base","")
            local=text.find(base, max(0,cursor-len(card["token"])))
            if local >= 0 and local < cursor:
                rx=full_x+draw.textbbox((0,0),text[:local],font=jf)[2]
                outlined(draw,(rx,295),ruby["reading"],font(28),body,2)
        rf=font(34); rw=draw.textbbox((0,0),card["romaji"],font=rf)[2]
        outlined(draw,(px+(pw-rw)/2,430),card["romaji"],rf,body,2)
    translation=frame["caption"]["translationZh"]
    tf=fit(draw,translation,45,30,int(W*.86)); lines=wrap(draw,translation,tf,int(W*.86))[:2]
    for i,line in enumerate(lines):
        lw=draw.textbbox((0,0),line,font=tf)[2]; outlined(draw,((W-lw)/2,500+i*52),line,tf,(245,245,245,245),3)
    if cards:
        gap,total,x=12,1730,95; cw=(total-gap*(len(cards)-1))//len(cards)
        for card in cards:
            right=x+cw; layer=Image.new("RGBA",(W,H),(0,0,0,0)); ld=ImageDraw.Draw(layer)
            ld.rounded_rectangle((x,600,right,850),radius=20,fill=hx(palette["accent"])+(128,),outline=hx(palette["activeTint"])+(220,),width=2)
            image.alpha_composite(layer); draw=ImageDraw.Draw(image); inner=cw-28
            tok=fit(draw,card["token"],37,16,inner); pos=fit(draw,card["posZh"],25,14,inner); meaning=card.get("functionZh",card.get("zhMeaning","")); mf=fit(draw,meaning,26,15,inner); ml=wrap(draw,meaning,mf,inner)[:2]
            for y,value,fnt in ((625,card["token"],tok),(770,card["posZh"],pos)):
                bw=draw.textbbox((0,0),value,font=fnt)[2]; outlined(draw,(x+(cw-bw)/2,y),value,fnt,"white",2)
            for i,line in enumerate(ml):
                bw=draw.textbbox((0,0),line,font=mf)[2]; outlined(draw,(x+(cw-bw)/2,690+i*32),line,mf,"white",2)
            x=right+gap
    image.save(path)

def main():
    RUN.mkdir(parents=True,exist_ok=True); OVER.mkdir(parents=True,exist_ok=True)
    frames=load(P/"frames.json")["frames"]; qrc=load(P/"timing"/"qm.json")["lines"]; palette=load(P/"palette.json")
    display_timing=load(P/"presentation.json")["foreground"].get("displayTiming", {})
    pre_roll=int(display_timing.get("preRollMs", 0)); post_roll=int(display_timing.get("postRollMs", 0))
    qrc_by_start={line["startMs"]:line for line in qrc}; transparent=OVER/"blank.png"; Image.new("RGBA",(W,H),(0,0,0,0)).save(transparent)
    concat=[]; matches=[]; cursor=0; seq=0
    def add(file, duration):
        nonlocal seq
        if duration<=0: return
        concat.append((file,duration)); seq+=1
    items=[]
    for frame in sorted(frames,key=lambda item:item["startMs"]):
        row=qrc_by_start.get(frame["startMs"])
        if not row: matches.append({"frameId":frame["id"],"mode":"unmatched","reason":"start time absent"}); continue
        mode="full" if norm(row["text"])==norm(frame["caption"]["japanese"]) else "unmatched"
        matches.append({"frameId":frame["id"],"mode":mode,"qrcStartMs":row["startMs"],"qrcText":row["text"]})
        items.append((frame,row,mode))
    for item_index,(frame,row,mode) in enumerate(items):
        next_start = items[item_index+1][1]["startMs"] if item_index+1 < len(items) else DURATION
        desired_start=max(0,row["startMs"]-pre_roll)
        desired_end=min(DURATION,row["endMs"]+post_roll)
        next_preroll=max(row["endMs"],next_start-pre_roll)
        display_start=max(desired_start,cursor)
        display_end=max(row["endMs"],min(desired_end,next_preroll))
        if display_start>cursor: add(transparent,display_start-cursor); cursor=display_start
        # Pre-roll, breaths, and tail hold retain the complete line without an active token.
        parts=row["parts"]
        for index,part in enumerate(parts):
            start=part["startMs"]; end=start+part["durationMs"]
            if start>cursor:
                png=OVER/f"{seq:05}.png"; render_state(frame,parts,-1,palette,png); add(png,start-cursor); cursor=start
            png=OVER/f"{seq:05}.png"; render_state(frame,parts,index if mode=="full" else -1,palette,png); add(png,end-start); cursor=max(cursor,end)
        if display_end>cursor:
            png=OVER/f"{seq:05}.png"; render_state(frame,parts,-1,palette,png); add(png,display_end-cursor); cursor=display_end
    if cursor<DURATION: add(transparent,DURATION-cursor)
    concat_path=RUN/"foreground.concat.txt"
    lines=[]
    for file,duration in concat:
        lines += [f"file '{file.as_posix()}'",f"duration {duration/1000:.6f}"]
    # concat demuxer needs a repeated final item to retain final duration.
    lines.append(f"file '{concat[-1][0].as_posix()}'")
    concat_path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    dump(RUN/"timing-match-report.json",{"schemaVersion":1,"matches":matches,"summary":{"full":sum(m["mode"]=="full" for m in matches),"unmatched":sum(m["mode"]=="unmatched" for m in matches)}})
    candidate=RUN/"mayocchauwa--16x9--20260821-r02-line-hold.mkv"
    fc="[0:v]fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih):black,setpts=PTS-STARTPTS[bg];[1:v]fps=30,format=rgba,setpts=PTS-STARTPTS[fg];[bg][fg]overlay=0:0:format=auto,fps=30,format=yuv420p[v]"
    cmd=["ffmpeg","-y","-v","error","-stream_loop","-1","-i",str(S/"background.mp4"),"-f","concat","-safe","0","-i",str(concat_path),"-i",str(S/"music.flac"),"-filter_complex",fc,"-map","[v]","-map","2:a:0","-t",f"{DURATION/1000:.6f}","-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-r","30","-fps_mode","cfr","-c:a","copy",str(candidate)]
    subprocess.run(cmd,check=True)
    print(json.dumps({"candidate":str(candidate),"states":len(concat),"fullMatches":sum(m["mode"]=="full" for m in matches)},ensure_ascii=False))

if __name__=="__main__": main()
