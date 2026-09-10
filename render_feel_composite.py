import json, subprocess, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent; OUT=ROOT/'output'; data=json.loads((ROOT/'feel-my-soul.frames.approved.json').read_text(encoding='utf8')); qrc=json.loads((OUT/'feel-qm.parsed.json').read_text(encoding='utf8'))
W,H=1920,1080; DELAY=1000; font='C:/Windows/Fonts/msyhbd.ttc'; cover=Image.open(ROOT/'feel-my-soul-cover.jpg').convert('RGBA'); audio=str(ROOT/'feel-my-soul-source.m4a'); bg=r'C:/Users/eke_l/Desktop/【Hi-Res】feel_my_soul_无字版_败犬女主太多了【NCED3】.26084770155.mp4'
DIR=OUT/'feel_overlay_segments'; DIR.mkdir(exist_ok=True)
def F(n): return ImageFont.truetype(font,n)
def hira(t): return ''.join(chr(ord(c)-0x60) if '\u30a1'<=c<='\u30f6' else c for c in t)
def kanji(t): return any('\u4e00'<=c<='\u9fff' for c in t)
def kana(t): return all(('ぁ'<=c<='ゖ') or ('ァ'<=c<='ヺ') or c in 'ー・' for c in t)
def ruby_parts(base, reading):
 """Attach reading only to kanji runs; literal kana remains unannotated."""
 reading=hira(reading); parts=[]; pos=0; i=0
 while i<len(base):
  j=i
  is_kanji='\u4e00'<=base[i]<='\u9fff'
  while j<len(base) and (('\u4e00'<=base[j]<='\u9fff')==is_kanji): j+=1
  chunk=base[i:j]
  if not is_kanji:
   expected=hira(chunk)
   if reading[pos:pos+len(expected)]==expected: pos+=len(expected)
   parts.append((chunk,None)); i=j; continue
  # Kanji reading ends immediately before the next literal-kana run (if any).
  next_kana=''
  k=j
  while k<len(base) and not ('\u4e00'<=base[k]<='\u9fff'):
   next_kana+=hira(base[k]); k+=1
  stop=reading.find(next_kana,pos) if next_kana else -1
  ruby=reading[pos:stop] if stop>=pos else reading[pos:]
  pos += len(ruby)
  parts.append((chunk,ruby or None)); i=j
 return parts
def centered(d,y,t,f,fill='white'):
 b=d.textbbox((0,0),t,font=f); d.text(((W-(b[2]-b[0]))/2,y),t,font=f,fill=fill)
def clean_pos(t):
 # Strip accidental display-label prefixes left in manually edited POS fields.
 return str(t).lstrip(':： ').replace('词性：','').replace('词性:','').strip()
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
 target=norm(fr['caption']['japanese'])
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
timeline_cursor=0
for fr in data['frames']:
 start,end=fr['startMs'],fr['endMs']
 if timeline_cursor < start:
  frames.append((timeline_cursor+DELAY,start+DELAY,{'kind':'intro'},None))
  timeline_cursor=start
 if fr['kind']!='lyric':
  frames.append((start+DELAY,end+DELAY,fr,None)); timeline_cursor=max(timeline_cursor,end); continue
 matched=qrc_match(fr)
 if not matched:
  # Text disagreement: preserve the timing and show the whole line unhighlighted.
  frames.append((start+DELAY,end+DELAY,fr,None)); timeline_cursor=max(timeline_cursor,end); continue
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
 timeline_cursor=max(timeline_cursor,end)
if timeline_cursor < data['project']['durationMs']:
 frames.append((timeline_cursor+DELAY,data['project']['durationMs']+DELAY,{'kind':'intro'},None))
def render(fr,active,path):
 im=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im,'RGBA')
 # A subtle veil is always present; it keeps the visual language stable in instrumental gaps.
 d.rectangle((0,0,W,H),fill=(0,0,0,38))
 if fr['kind']=='lyric':
  # A second, stronger veil appears only with learning content for reliable mobile contrast.
  d.rectangle((0,0,W,H),fill=(0,0,0,72))
  c=cover.copy(); c.thumbnail((220,220)); im.alpha_composite(c,((W-c.width)//2,42))
  cap=fr['caption']; ruby=cap['furigana']; mf=F(78); rf=F(30); widths=[d.textbbox((0,0),x['base'],font=mf)[2] for x in ruby]; gap=12; x=(W-(sum(widths)+gap*(len(widths)-1)))/2
  if not ruby:
   # English-only lyrics intentionally carry no Japanese reading or study cards.
   centered(d,390,cap['japanese'],F(64),'white')
  else:
   for idx,(item,w) in enumerate(zip(ruby,widths)):
    color='#FF5A70' if idx==active else 'white'
    part_x=x
    for base_part, ruby_part in ruby_parts(item['base'],item['reading']):
     d.text((part_x,360),base_part,font=mf,fill=color)
     if ruby_part:
      d.text((part_x,320),ruby_part,font=rf,fill=color)
     part_x+=d.textbbox((0,0),base_part,font=mf)[2]
    r=item['romaji']; b=d.textbbox((0,0),r,font=F(34)); d.text((x+(w-(b[2]-b[0]))/2,485),r,font=F(34),fill=color); x+=w+gap
  centered(d,595,cap['translationZh'],F(46),(245,245,245,235)); cards=fr['grammarCards']; n=max(1,len(cards)); total=1740; gap=12; widths=[total//n]*n; widths[-1]+=total-sum(widths); x=90
  for card,w in zip(cards,widths):
   d.rounded_rectangle((x,705,x+w-gap,950),20,fill=(122,18,35,128),outline=(255,150,160,130),width=2); cx=x+(w-gap)/2
   for y,t,sz in [(730,card['token'],36),(795,clean_pos(card.get('functionZh',card['zhMeaning'])),27),(855,clean_pos(card['posZh']),26)]:
    b=d.textbbox((0,0),t,font=F(sz)); d.text((cx-(b[2]-b[0])/2,y),t,font=F(sz),fill='white')
   x+=w
 im.save(path)
concat=[]
for i,(start,end,fr,active) in enumerate(frames):
 if end<=start: continue
 p=DIR/f'{i:04d}.png'; render(fr,active,p); concat += [f"file '{p.as_posix()}'",f'duration {(end-start)/1000:.3f}']
concat += [f"file '{(DIR/f'{len(frames)-1:04d}.png').as_posix()}'"]
cf=OUT/'feel_overlay.concat.txt'; cf.write_text('\n'.join(concat),encoding='utf8')
target=OUT/'feel-my-soul-qrc-composite.mp4'
subprocess.run(['ffmpeg','-y','-v','error','-stream_loop','-1','-i',bg,'-f','concat','-safe','0','-i',str(cf),'-i',audio,'-filter_complex',f'[1:v]format=rgba[ov];[0:v][ov]overlay=0:0:format=auto,format=yuv420p[v];[2:a]adelay={DELAY}:all=1[a]','-map','[v]','-map','[a]','-r','24000/1001','-c:v','libx264','-crf','18','-c:a','aac','-b:a','320k','-shortest',str(target)],check=True)
print(target)
