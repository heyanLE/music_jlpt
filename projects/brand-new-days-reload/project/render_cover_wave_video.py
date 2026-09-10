"""Render Brand New Days cover-wave learning video from the safe QQ Music draft."""
import json, math, os, subprocess, unicodedata
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).parent; PROJECT=ROOT.parent; SOURCE=PROJECT/'source'; OUT=PROJECT/'deliverables'
DATA=json.loads((ROOT/'frames.json').read_text(encoding='utf8')); QRC=json.loads((OUT/'brand-new-days-qm.parsed.json').read_text(encoding='utf8'))
W,H,FPS=1920,1080,30; FONT='C:/Windows/Fonts/msyhbd.ttc'; ACCENT=(215,28,55); ACTIVE=(255,112,135); CARD=(103,10,30,190)
OUTLINE=(0,0,0,235)
COVER=Image.open(SOURCE/'COVER.jpg').convert('RGB'); AUDIO=SOURCE/'Brand New Days -Reload-.flac'; OVER=ROOT/'cover_wave_overlay'; OVER.mkdir(exist_ok=True)
def f(size): return ImageFont.truetype(FONT,size)
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if not c.isspace())
def japanese_norm(s): return ''.join(c for c in norm(s) if ('ぁ'<=c<='ゖ') or ('ァ'<=c<='ヺ') or ('一'<=c<='龯'))
def hira(s): return ''.join(chr(ord(c)-0x60) if 'ァ'<=c<='ヶ' else c for c in s)
def kanji(c): return '一'<=c<='龯'
def is_english(c): return c.isascii() and (c.isalpha() or c in " '-()!?.,")
def outlined(d,xy,s,font,fill,width):
 d.text(xy,s,font=font,fill=fill,stroke_width=width,stroke_fill=OUTLINE)
def center(d,y,s,font,fill,width=3):
 b=d.textbbox((0,0),s,font=font,stroke_width=width); outlined(d,((W-(b[2]-b[0]))/2,y),s,font,fill,width)
def ruby(base,read):
 read=hira(read); out=[]; p=i=0
 while i<len(base):
  j=i; k=kanji(base[i])
  while j<len(base) and kanji(base[j])==k:j+=1
  chunk=base[i:j]
  if not k:
   exp=hira(chunk)
   if read[p:p+len(exp)]==exp:p+=len(exp)
   out.append((chunk,None));i=j;continue
  follow='';z=j
  while z<len(base) and not kanji(base[z]):follow+=hira(base[z]);z+=1
  stop=read.find(follow,p) if follow else -1; r=read[p:stop] if stop>=p else read[p:];p+=len(r);out.append((chunk,r));i=j
 return out
def wrap(d,s,font,mw):
 lines=[];cur=''
 for ch in s:
  if cur and d.textbbox((0,0),cur+ch,font=font)[2]>mw:lines.append(cur);cur=ch
  else:cur+=ch
  if len(lines)==2:break
 if cur and len(lines)<2:lines.append(cur)
 return lines[:2]

def lyric_units_data(fr):
 # Keep every display unit in approved caption order; English units are timed too.
 text=fr['caption']['japanese']; cards=fr['grammarCards']; units=[]; pos=card_index=0
 while pos<len(text):
  if is_english(text[pos]):
   end=pos+1
   while end<len(text) and is_english(text[end]): end+=1
   value=text[pos:end].strip()
   if value: units.append(('english',value,None))
   pos=end;continue
  if card_index<len(cards) and text.startswith(cards[card_index]['token'],pos):
   token=cards[card_index]['token']; units.append(('card',token,card_index))
   pos+=len(token);card_index+=1;continue
  pos+=1
 return units

def lyric_units(fr, draw):
 size = 70 if not fr['grammarCards'] else 42
 return [(kind,value,index,draw.textbbox((0,0),value,font=f(size if kind=='english' else 70))[2]) for kind,value,index in lyric_units_data(fr)]

ql=[]
for row in QRC['content']:
 parts=[]
 for p in row.get('content',[]):
  tx=norm(p['content'])
  if tx:parts.append((row['start']+p['start'],row['start']+p['start']+p['duration'],tx))
 joined=''.join(p[2] for p in parts)
 if joined:ql.append((row['start'],row['start']+row['duration'],joined,parts))
def match(fr):
 # Prefer the full mixed-language caption so every displayed unit has one shared index.
 def find(target):
  hits=[]
  for i,(start,_,_,_) in enumerate(ql):
   joined='';pieces=[];end=start
   for _,le,lt,lp in ql[i:i+4]:
    joined+=norm(lt);pieces+=lp;end=le;off=joined.find(target)
    if off>=0:hits.append((abs(start-fr['startMs']),off,pieces))
    if end>fr['endMs']+1800:break
  return None if not hits else min(hits,key=lambda hit:hit[0])[1:]
 target=norm(fr['caption']['japanese']); hit=find(target)
 if hit:return (*hit,'full')
 # Keep Japanese token timing as a conservative fallback when supplied English differs.
 target=japanese_norm(fr['caption']['japanese']); hits=[]
 for i,(start,_,_,_) in enumerate(ql):
  joined='';pieces=[];end=start
  for _,le,lt,lp in ql[i:i+4]:
   joined+=japanese_norm(lt);pieces+=lp;end=le;off=joined.find(target)
   if off>=0:hits.append((abs(start-fr['startMs']),off,pieces))
   if end>fr['endMs']+1800:break
 return None if not hits else (*min(hits,key=lambda hit:hit[0])[1:],'japanese')
timeline=[];cursor=0;last_frame=DATA['frames'][0]
for fr in DATA['frames']:
 start,end=fr['startMs'],fr['endMs']
 if cursor<start:timeline.append((cursor,start,last_frame,None))
 cursor=max(cursor,end);hit=match(fr)
 if not hit:timeline.append((start,end,fr,None));continue
 off,pieces,match_mode=hit;n=0;ends=[]
 units=lyric_units_data(fr) if match_mode=='full' else [('card',c['token'],index) for index,c in enumerate(fr['grammarCards'])]
 for kind,value,index in units:n+=len(norm(value));ends.append((n,kind,index))
 local=start;source=0
 for ps,pe,tx in pieces:
  timed=norm(tx) if match_mode=='full' else japanese_norm(tx);before=source;source+=len(timed);a,b=max(before,off),min(source,off+n)
  if a>=b:continue
  ps,pe=max(ps,start),min(pe,end)
  if local<ps:timeline.append((local,ps,fr,None))
  pos=a-off; active=next(((kind,index) for end,kind,index in ends if pos<end),None)
  if pe>ps:timeline.append((ps,pe,fr,active))
  local=max(local,pe)
 if local<end:timeline.append((local,end,fr,None))
 last_frame=fr
if cursor<352600:timeline.append((cursor,352600,last_frame,None))

def make_horizon_pulse_background(duration_ms):
 # B: glass stems driven by real log-spaced FFT bands. The black encoder base
 # is removed by colorkey during composition, so the blurred cover stays visible.
 pcm=ROOT/'cover_wave_mono.f32le'; target=ROOT/'cover_wave_glass_stems_v1.mp4'
 if target.exists(): return target
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(AUDIO),'-ac','1','-ar','8000','-f','f32le',str(pcm)],check=True)
 samples=np.fromfile(pcm,dtype=np.float32)
 proc=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1848x150','-r',str(FPS),'-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','18',str(target)],stdin=subprocess.PIPE)
 bars=64; fft_size=2048; window=np.hanning(fft_size); edges=np.geomspace(2,fft_size//2,bars+1).astype(int); previous=np.zeros(bars)
 try:
  for index in range(math.ceil(duration_ms/1000*FPS)):
   center=int(index/FPS*8000); block=np.zeros(fft_size,dtype=np.float32); start=max(0,center-fft_size//2); end=min(len(samples),center+fft_size//2)
   block[start-(center-fft_size//2):start-(center-fft_size//2)+(end-start)]=samples[start:end]
   magnitude=np.abs(np.fft.rfft(block*window)); raw=np.array([magnitude[edges[i]:max(edges[i]+1,edges[i+1])].mean() for i in range(bars)])
   raw=np.clip(np.log1p(raw*36)/5.2,0,1); previous=np.where(raw>previous,previous+(raw-previous)*0.58,previous+(raw-previous)*0.13)
   image=Image.new('RGBA',(1848,150),(0,0,0,255)); draw=ImageDraw.Draw(image,'RGBA'); glow=Image.new('RGBA',(1848,150),(0,0,0,0)); gd=ImageDraw.Draw(glow,'RGBA')
   gap=11; width=(1848-gap*(bars-1))//bars
   for i,value in enumerate(previous):
    x=i*(width+gap); height=int(18+112*value); color=tuple(round(ACCENT[c]*(1-i/(bars-1))+ACTIVE[c]*i/(bars-1)) for c in range(3))
    gd.rounded_rectangle((x,150-height,x+width,150),radius=max(2,width//2),fill=color+(100,))
   image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(11)))
   for i,value in enumerate(previous):
    x=i*(width+gap); height=int(18+112*value); color=tuple(round(ACCENT[c]*(1-i/(bars-1))+ACTIVE[c]*i/(bars-1)) for c in range(3))
    draw.rounded_rectangle((x,150-height,x+width,150),radius=max(2,width//2),fill=color+(142,))
    draw.rounded_rectangle((x-1,147-height,x+width+1,153-height),radius=3,fill=ACTIVE+(235,))
   proc.stdin.write(image.convert('RGB').tobytes())
 finally:
  proc.stdin.close()
  if proc.wait()!=0: raise RuntimeError('horizon visualizer encode failed')
 return target

base=COVER.resize((W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30)).convert('RGBA')
base=Image.alpha_composite(base,Image.new('RGBA',(W,H),(0,0,0,105)))
BACKGROUND=ROOT/'cover_wave_background.png'
base.convert('RGB').save(BACKGROUND)
def render(fr,active,path):
 # Keep this layer transparent: the blurred cover and waveform are a real background.
 image=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(image,'RGBA')
 # cover-wave keeps the learning foreground visible, including gaps between sung lines.
 image=Image.alpha_composite(image,Image.new('RGBA',(W,H),(0,0,0,118)));d=ImageDraw.Draw(image,'RGBA')
 small=COVER.resize((220,220),Image.Resampling.LANCZOS);image.alpha_composite(small.convert('RGBA'),(850,35));d=ImageDraw.Draw(image,'RGBA')
 cards=fr['grammarCards']; units=lyric_units(fr,d); gap=22
 x=(W-sum(unit[3] for unit in units)-gap*(len(units)-1))/2
 for kind,value,i,wid in units:
  if kind=='english':
   color=ACTIVE if active==('english',i) else (255,255,255,235)
   outlined(d,(x,352),value,f(70 if not cards else 42),color,4);x+=wid+gap;continue
  card=cards[i]
  color=ACTIVE if active==('card',i) else 'white';px=x
  if card.get('sourceWord'):
   source_font=f(23); source=card['sourceWord']; source_box=d.textbbox((0,0),source,font=source_font)
   outlined(d,(x+(wid-(source_box[2]-source_box[0]))/2,295),source,source_font,color,2)
  for ba,re in ruby(card['token'],card['reading']):
   outlined(d,(px,330),ba,f(70),color,4)
   if re:outlined(d,(px,295),re,f(28),color,2)
   px+=d.textbbox((0,0),ba,font=f(70))[2]
  rb=d.textbbox((0,0),card['romaji'],font=f(34));outlined(d,(x+(wid-(rb[2]-rb[0]))/2,430),card['romaji'],f(34),color,2);x+=wid+gap
 center(d,500,fr['caption']['translationZh'],f(45),(245,245,245,240),3)
 if cards:
  total=1730;gap=12;x=95;cw=total//len(cards)
  for card in cards:
   d.rounded_rectangle((x,600,x+cw-gap,850),20,fill=CARD,outline=ACTIVE+(145,),width=2);mid=x+(cw-gap)/2
   for yy,txt,font in [(625,card['token'],f(37))]:
    b=d.textbbox((0,0),txt,font=font);outlined(d,(mid-(b[2]-b[0])/2,yy),txt,font,'white',2)
   meaning_font=f(26); meaning=card.get('functionZh',card.get('zhMeaning','待审')); meaning_lines=wrap(d,meaning,meaning_font,cw-gap-34)
   meaning_top=695 if len(meaning_lines)==1 else 678
   for line_index,line in enumerate(meaning_lines):
    b=d.textbbox((0,0),line,font=meaning_font);outlined(d,(mid-(b[2]-b[0])/2,meaning_top+line_index*32),line,meaning_font,'white',2)
   txt=card['posZh']; font=f(25)
   b=d.textbbox((0,0),txt,font=font);outlined(d,(mid-(b[2]-b[0])/2,770),txt,font,'white',2)
   x+=cw
 image.save(path)
concat=[]
for i,(s,e,fr,act) in enumerate(timeline):
 if e<=s:continue
 p=OVER/f'{i:04d}.png';render(fr,act,p);concat += [f"file '{p.as_posix()}'",f'duration {(e-s)/1000:.3f}']
concat += [f"file '{(OVER/f'{len(timeline)-1:04d}.png').as_posix()}'"]
cp=ROOT/'cover_wave.concat.txt';cp.write_text('\n'.join(concat),encoding='utf8')
if os.environ.get('FOREGROUND_ONLY') == '1':
 print(cp, 'segments',len(timeline))
 raise SystemExit(0)
BAR_BACKGROUND=make_horizon_pulse_background(max(end for _,end,_,_ in timeline))
FINAL=OUT/'final'; FINAL.mkdir(exist_ok=True)
target=FINAL/'brand-new-days-reload--cover-wave-glass-stems--20260815-r02.mp4'
graph=("[0:v]fps=30,format=rgba[bg];"
       "[3:v]fps=30,format=rgba,colorkey=0x000000:0.035:0.0[wave];"
       "[bg][wave]overlay=36:925:format=auto[wavebg];"
       "[1:v]fps=30,format=rgba[fg];"
       "[wavebg][fg]overlay=0:0:format=auto,fps=30,format=yuv420p[v]")
subprocess.run(['ffmpeg','-y','-v','error','-loop','1','-framerate','30','-i',str(BACKGROUND),'-f','concat','-safe','0','-i',str(cp),'-i',str(AUDIO),'-i',str(BAR_BACKGROUND),'-filter_complex',graph,'-map','[v]','-map','2:a','-t',f'{max(end for _,end,_,_ in timeline)/1000:.3f}','-c:v','libx264','-pix_fmt','yuv420p','-crf','18','-r','30','-fps_mode','cfr','-c:a','aac','-b:a','320k',str(target)],check=True)
print(target, 'segments',len(timeline))
