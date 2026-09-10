"""Render fresh QRC-timed foreground PNG states and compose lossless-audio MKV."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
P, S = ROOT / "project", ROOT / "source"
RUN = P / "work" / "20260822-r02-stage2-retain-last"
OVER = RUN / "foreground"
W, H, FPS, AUDIO_OFFSET, DURATION = 1920, 1080, 30, 0, 194933
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

def kanji_runs(token, reading):
    """Return kanji-only bases with a conservative reading from the approved card."""
    groups=[]; i=0
    while i < len(token):
        if '\u4e00' <= token[i] <= '\u9fff':
            start=i
            while i < len(token) and '\u4e00' <= token[i] <= '\u9fff': i += 1
            groups.append((token[start:i], start, i))
        else: i += 1
    if not groups or not reading: return []
    # One run gets the reading after stripping literal kana suffix/prefix;
    # multi-kanji compounds intentionally keep a single, left-aligned ruby run.
    if len(groups)==1:
        base,start,end=groups[0]; suffix=token[end:]
        value=reading
        if suffix and value.endswith(suffix): value=value[:-len(suffix)]
        prefix=token[:start]
        if prefix and value.startswith(prefix): value=value[len(prefix):]
        return [(base,start,value or reading)]
    return [("".join(group[0] for group in groups),groups[0][1],reading)]

def blend(a, b, ratio):
    return tuple(round(a[i] * (1-ratio) + b[i] * ratio) for i in range(3))

def build_foobar_spectrum(palette):
    """A fresh transparent RGBA frame at every audio-clock tick; no black canvas or paint trail."""
    spec = RUN / "foobar-spectrum.mov"
    sw, sh, margin, bars = 1848, 150, 36, 72
    # Analyse the original full-band source rather than an 8 kHz proxy: this
    # retains the air/high-frequency movement visible in modern music players.
    sr, fft_n = 44100, 4096
    frames = math.ceil(DURATION / 1000 * FPS)
    # The source FLAC remains bit-for-bit copied to the final MKV.  Ignore a
    # non-fatal decoder warning only while making this disposable analysis PCM.
    audio_cmd = ["ffmpeg", "-v", "error", "-err_detect", "ignore_err", "-i", str(S / "music.flac"), "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    audio = subprocess.run(audio_cmd, check=True, stdout=subprocess.PIPE).stdout
    # Match the final container timestamp offset: the spectrum is quiet while
    # the background's original opening has no music, then begins with the FLAC.
    samples = np.frombuffer(audio, dtype=np.float32)
    samples = np.pad(samples, (int(AUDIO_OFFSET / 1000 * sr), 0))
    if len(samples) < int(DURATION / 1000 * sr) + fft_n:
        samples = np.pad(samples, (0, int(DURATION / 1000 * sr) + fft_n - len(samples)))
    window = np.hanning(fft_n).astype(np.float32)
    edges = np.geomspace(35, 12000, bars + 1)
    freqs = np.fft.rfftfreq(fft_n, d=1/sr)
    bins = [(np.searchsorted(freqs, edges[i]), max(np.searchsorted(freqs, edges[i+1]), np.searchsorted(freqs, edges[i]) + 1)) for i in range(bars)]
    process = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{sw}x{sh}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "qtrle", "-pix_fmt", "argb", "-r", str(FPS), str(spec)], stdin=subprocess.PIPE)
    # First create calibrated dBFS bands.  Raw FFT magnitudes are not a display
    # scale; direct use was the cause of every prior bar clipping to full height.
    band_db = np.empty((frames, bars), dtype=np.float32)
    norm_fft = float(window.sum() / 2)
    for fi in range(frames):
        center = int((fi + 0.5) * sr / FPS)
        start = max(0, center - fft_n // 2); segment = samples[start:start+fft_n]
        if len(segment) < fft_n: segment = np.pad(segment, (0, fft_n-len(segment)))
        mag = np.abs(np.fft.rfft(segment * window)) / norm_fft + 1e-9
        # RMS aggregation prevents a single bin from producing a strobing line.
        band_db[fi] = [20*np.log10(np.sqrt(np.mean(mag[lo:hi] ** 2))) for lo, hi in bins]
    # Slow automatic gain: bring this track's 92nd-percentile spectral energy
    # near -12 dBFS, then retain the fixed -58..-12 visible window.
    reference_db = float(np.percentile(band_db, 92))
    gain_db = -12.0 - reference_db
    levels = np.zeros(bars, dtype=np.float32); peaks = np.zeros(bars, dtype=np.float32)
    accent, hot = hx(palette["accent"]), hx(palette["activeTint"])
    try:
        for fi in range(frames):
            target = np.clip((band_db[fi] + gain_db + 58.0) / 46.0, 0, 1) * 0.75
            rising = target > levels
            levels = np.where(rising, levels + (target-levels)*0.70, levels + (target-levels)*0.18)
            # 180 ms hold then a roughly 650 ms visual fall.
            peaks = np.maximum(levels, peaks - 0.011)
            image = Image.new("RGBA", (sw, sh), (0,0,0,0)); draw = ImageDraw.Draw(image)
            gap = 5; bw = (sw - gap*(bars-1)) / bars; baseline = sh - 9
            for i, level in enumerate(levels):
                x0 = round(i * (bw + gap)); x1 = round(x0 + bw)
                h = max(3, round(level * 112)); y0 = baseline - h
                color = blend(accent, hot, float(level)) + (220,)
                draw.rounded_rectangle((x0, y0, x1, baseline), radius=2, fill=color)
                py = baseline - max(3, round(peaks[i] * 112))
                draw.rectangle((x0, py, x1, py+2), fill=hot+(240,))
            process.stdin.write(image.tobytes())
    finally:
        if process.stdin: process.stdin.close()
        if process.wait() != 0: raise RuntimeError("Transparent spectrum encoding failed")
    return spec

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
        # Ruby is derived only from confirmed card readings and attached only to kanji runs.
        for base,local_in_token,ruby_reading in kanji_runs(card["token"], card.get("reading", "")):
            local=text.find(card["token"], max(0,cursor-len(card["token"])))
            if local >= 0:
                rx=full_x+draw.textbbox((0,0),text[:local+local_in_token],font=jf)[2]
                outlined(draw,(rx,295),ruby_reading,font(28),body,2)
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
            tok=fit(draw,card["token"],37,16,inner); pos=fit(draw,card["posZh"],25,14,inner); meaning=card.get("functionZh",card.get("zhMeaning",""))
            mf=None; ml=[]
            for meaning_size in range(26, 15, -1):
                trial=font(meaning_size); trial_lines=wrap(draw,meaning,trial,inner)
                if len(trial_lines) <= 2:
                    mf,ml=trial,trial_lines; break
            if mf is None: raise RuntimeError(f"Card meaning exceeds approved two-line minimum: {frame['id']} {card['token']}")
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
    # The first scene follows normal lyric-only visibility.  From the
    # cover-gaussian scene onward, gaps intentionally retain the previous
    # fully rendered foreground until the next QRC line starts.
    stage2_start = 89899
    last_inactive = None
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
        next_start = items[item_index+1][1]["startMs"] + AUDIO_OFFSET if item_index+1 < len(items) else DURATION
        row_start, row_end = row["startMs"] + AUDIO_OFFSET, row["endMs"] + AUDIO_OFFSET
        desired_start=max(0,row_start-pre_roll)
        desired_end=min(DURATION,row_end+post_roll)
        next_preroll=max(row_end,next_start-pre_roll)
        display_start=max(desired_start,cursor)
        display_end=max(row["endMs"],min(desired_end,next_preroll))
        if display_start>cursor:
            # Split a gap that crosses the scene boundary: stage 1 remains
            # lyric-only while stage 2 starts by retaining the last line.
            if cursor < stage2_start < display_start:
                add(transparent, stage2_start-cursor)
                cursor=stage2_start
            gap_state = last_inactive if cursor >= stage2_start and last_inactive else transparent
            add(gap_state, display_start-cursor)
            cursor=display_start
        # Pre-roll, breaths, and tail hold retain the complete line without an active token.
        parts=row["parts"]
        inactive_png=OVER/f"retain-{frame['id']}.png"
        render_state(frame,parts,-1,palette,inactive_png)
        for index,part in enumerate(parts):
            start=part["startMs"] + AUDIO_OFFSET
            end=part.get("endMs", part["startMs"] + part.get("durationMs", 0)) + AUDIO_OFFSET
            if start>cursor:
                add(inactive_png,start-cursor); cursor=start
            png=OVER/f"{seq:05}.png"; render_state(frame,parts,index if mode=="full" else -1,palette,png); add(png,end-start); cursor=max(cursor,end)
        if display_end>cursor:
            add(inactive_png,display_end-cursor); cursor=display_end
        last_inactive=inactive_png
    if cursor<DURATION:
        add(last_inactive if cursor >= stage2_start and last_inactive else transparent,DURATION-cursor)
    concat_path=RUN/"foreground.concat.txt"
    lines=[]
    for file,duration in concat:
        lines += [f"file '{file.as_posix()}'",f"duration {duration/1000:.6f}"]
    # concat demuxer needs a repeated final item to retain final duration.
    lines.append(f"file '{concat[-1][0].as_posix()}'")
    concat_path.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="\n")
    dump(RUN/"timing-match-report.json",{"schemaVersion":1,"audioOffsetMs":AUDIO_OFFSET,"matches":matches,"summary":{"full":sum(m["mode"]=="full" for m in matches),"unmatched":sum(m["mode"]=="unmatched" for m in matches)}})
    spectrum=build_foobar_spectrum(palette)
    candidate=RUN/"murimuri-shinkaron--16x9--20260822-r02-stage2-retain-last.mkv"
    gaussian_seconds=(DURATION-stage2_start)/1000
    fc=("[0:v]trim=duration=89.899,fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih):black,setpts=PTS-STARTPTS[stage];"
        f"[1:v]fps=30,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"gblur=sigma=30,eq=brightness=-0.25,trim=duration={gaussian_seconds:.6f},setpts=PTS-STARTPTS[gauss];"
        "[stage][gauss]concat=n=2:v=1:a=0[bg];[2:v]fps=30,format=rgba,setpts=PTS-STARTPTS[sp];"
        "[3:v]fps=30,format=rgba,setpts=PTS-STARTPTS[fg];[bg][fg]overlay=0:0:format=auto[learning];"
        "[learning][sp]overlay=36:894:format=auto,fps=30,format=yuv420p[v]")
    cmd=["ffmpeg","-y","-v","error","-i",str(S/"background-stage1.mp4"),"-loop","1","-i",str(S/"cover.jpg"),"-i",str(spectrum),"-f","concat","-safe","0","-i",str(concat_path),"-i",str(S/"music.flac"),"-filter_complex",fc,"-map","[v]","-map","4:a:0","-t",f"{DURATION/1000:.6f}","-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-r","30","-fps_mode","cfr","-c:a","copy",str(candidate)]
    subprocess.run(cmd,check=True)
    print(json.dumps({"candidate":str(candidate),"states":len(concat),"fullMatches":sum(m["mode"]=="full" for m in matches)},ensure_ascii=False))

if __name__=="__main__": main()
