import json, subprocess, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent; OUT=ROOT/'output'; data=json.loads((ROOT/'love2000.frames.approved.json').read_text(encoding='utf8')); qrc=json.loads((OUT/'love2000.qrc.parsed.json').read_text(encoding='utf8'))
W,H=1920,1080; DELAY=1000; font='C:/Windows/Fonts/msyh.ttc'; cover=Image.open(ROOT/'love2000-cover.jpg').convert('RGBA'); audio='C:/Users/eke_l/Music/遠野ひかる - LOVE 2000_EM.flac'; bg='C:/Users/eke_l/Desktop/【Hi-Res】LOVE2000败犬老八无字版【NCED1】.26084639254.mp4'
DIR=OUT/'qrc_overlay_segments'; DIR.mkdir(exist_ok=True)
def F(n): return ImageFont.truetype(font,n)
def hira(t): return ''.join(chr(ord(c)-0x60) if '\u30a1'<=c<='\u30f6' else c for c in t)
def kanji(t): return any('\u4e00'<=c<='\u9fff' for c in t)
def centered(d,y,t,f,fill='white'):
 b=d.textbbox((0,0),t,font=f); d.text(((W-(b[2]-b[0]))/2,y),t,font=f,fill=fill)
# Normalize the two lyric sources before matching: QQ uses lower-case "news",
# while the reviewed display copy uses "NEWS".  NFKC also eliminates harmless
# full-width/half-width differences without touching the shown lyric text.
def norm(t): return ''.join(c for c in unicodedata.normalize('NFKC',t).casefold() if not c.isspace())
qrc_lines=[]
for line in qrc['content']:
 parts=[]
 for part in line['content']:
  text=part['content']; clean=norm(text)
  if clean:
   parts.append((line['start']+part['start'],line['start']+part['start']+part['duration'],clean))
 text=''.join(p[2] for p in parts)
 if text: qrc_lines.append((line['start'],line['start']+line['duration'],text,parts))

def qrc_match(fr):
 """Return an exact reviewed-lyric match, allowing QRC to split a sung line."""
 target=norm(''.join(c['token'] for c in fr['grammarCards']))
 candidates=[]
 for i,(start,_,_,_) in enumerate(qrc_lines):
  text=''; parts=[]; end=start
  # QQ Music sometimes breaks a displayed lyric into breath-sized QRC lines.
  # A short rolling join preserves those per-character timings.
  for _,line_end,line_text,line_parts in qrc_lines[i:i+4]:
   text+=line_text; parts+=line_parts; end=line_end
   at=text.find(target)
   if at >= 0:
    # Prefer the time-nearest exact text match if a refrain repeats.
    candidates.append((abs(start-fr['startMs']),at,start,end,text,parts))
   if end>fr['endMs']+1500: break
 if not candidates: return None
 _,at,start,end,text,parts=min(candidates)
 return target,at,start,end,text,parts
frames=[(0,DELAY,{'kind':'intro'},None)]
for fr in data['frames']:
 start,end=fr['startMs'],fr['endMs']
 if fr['kind']!='lyric': frames.append((start+DELAY,end+DELAY,fr,None)); continue
 matched=qrc_match(fr)
 if not matched:
  # Text disagreement: preserve the timing and show the whole line unhighlighted.
  frames.append((start+DELAY,end+DELAY,fr,None)); continue
 target,offset,_,_,_,parts=matched; tokens=fr['grammarCards']; cursor=start
 card_ends=[]; total=0
 for card in tokens:
  total+=len(norm(card['token'])); card_ends.append(total)
 source_pos=0
 for es,ee,text in parts:
  part_start=source_pos; source_pos+=len(text)
  overlap_start=max(part_start,offset); overlap_end=min(source_pos,offset+len(target))
  if overlap_start>=overlap_end: continue
  es=max(es,start); ee=min(ee,end)
  if cursor<es: frames.append((cursor+DELAY,es+DELAY,fr,None))
  pos=overlap_start-offset
  active=next((i for i,boundary in enumerate(card_ends) if pos<boundary),None)
  if ee>es: frames.append((es+DELAY,ee+DELAY,fr,active))
  cursor=max(cursor,ee)
 if cursor<end: frames.append((cursor+DELAY,end+DELAY,fr,None))
def render(fr,active,path):
 im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im,'RGBA')
 if fr['kind']=='lyric':
  # Keep the moving background readable without adding a panel or changing empty sections.
  d.rectangle((0,0,W,H),fill=(0,0,0,58))
  c=cover.copy(); c.thumbnail((220,220)); im.alpha_composite(c,((W-c.width)//2,42))
  cap=fr['caption']; ruby=cap['furigana']; mf=F(78); rf=F(30); widths=[d.textbbox((0,0),x['base'],font=mf)[2] for x in ruby]; gap=12; x=(W-(sum(widths)+gap*(len(widths)-1)))/2
  for idx,(item,w) in enumerate(zip(ruby,widths)):
   color='#FFD166' if idx==active else 'white'; d.text((x,360),item['base'],font=mf,fill=color)
   if kanji(item['base']): d.text((x,320),hira(item['reading']),font=rf,fill=color)
   r=item['romaji']; b=d.textbbox((0,0),r,font=F(34)); d.text((x+(w-(b[2]-b[0]))/2,485),r,font=F(34),fill=color); x+=w+gap
  centered(d,595,cap['translationZh'],F(46),(245,245,245,235)); cards=fr['grammarCards']; n=max(1,len(cards)); total=1740; gap=12; widths=[total//n]*n; widths[-1]+=total-sum(widths); x=90
  for card,w in zip(cards,widths):
   d.rounded_rectangle((x,705,x+w-gap,950),20,fill=(15,55,95,118),outline=(220,240,255,100),width=2); cx=x+(w-gap)/2
   for y,t,sz in [(730,card['token'],34),(795,card.get('functionZh',card['zhMeaning']),24),(855,card['posZh'],23)]:
    b=d.textbbox((0,0),t,font=F(sz)); d.text((cx-(b[2]-b[0])/2,y),t,font=F(sz),fill='white')
   x+=w
 im.save(path)
concat=[]
for i,(start,end,fr,active) in enumerate(frames):
 if end<=start: continue
 p=DIR/f'{i:04d}.png'; render(fr,active,p); concat += [f"file '{p.as_posix()}'",f'duration {(end-start)/1000:.3f}']
concat += [f"file '{(DIR/f'{len(frames)-1:04d}.png').as_posix()}'"]
cf=OUT/'qrc_overlay.concat.txt'; cf.write_text('\n'.join(concat),encoding='utf8')
target=OUT/'love2000-qrc-composite.mp4'
subprocess.run(['ffmpeg','-y','-v','error','-stream_loop','-1','-i',bg,'-f','concat','-safe','0','-i',str(cf),'-i',audio,'-filter_complex',f'[1:v]format=rgba[ov];[0:v][ov]overlay=0:0:format=auto,format=yuv420p[v];[2:a]adelay={DELAY}:all=1[a]','-map','[v]','-map','[a]','-r','24000/1001','-c:v','libx264','-crf','18','-c:a','aac','-b:a','320k','-shortest',str(target)],check=True)
print(target)
