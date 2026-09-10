import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).parent; source=ROOT/'love2000.frames.approved.json'; data=json.loads(source.read_text(encoding='utf8'))
OUT=ROOT/'output'; transparent='--transparent' in sys.argv; FR=OUT/('love2000_frames_transparent' if transparent else 'love2000_frames'); OUT.mkdir(exist_ok=True); FR.mkdir(exist_ok=True)
W,H=1920,1080; font='C:/Windows/Fonts/msyh.ttc'; cover=Image.open(ROOT/'love2000-cover.jpg').convert('RGB')
bg=cover.resize((W,H)).filter(ImageFilter.GaussianBlur(36)); bg=Image.blend(bg,Image.new('RGB',(W,H),(10,30,55)),.42)
def F(n): return ImageFont.truetype(font,n)
def hira(text):
    return ''.join(chr(ord(ch)-0x60) if '\u30a1' <= ch <= '\u30f6' else ch for ch in text)
def has_kanji(text):
    return any('\u4e00' <= ch <= '\u9fff' for ch in text)
def center(d,y,s,ft,fill='white'):
    box=d.textbbox((0,0),s,font=ft); d.text(((W-(box[2]-box[0]))/2,y),s,font=ft,fill=fill)
for i,fr in enumerate(data['frames']):
    im=Image.new('RGBA',(W,H),(0,0,0,0)) if transparent else bg.copy(); d=ImageDraw.Draw(im,'RGBA'); c=cover.copy(); c.thumbnail((220,220)); im.paste(c,((W-c.width)//2,42))
    if fr['kind']=='lyric':
      cap=fr['caption']; ruby=cap['furigana']; main_font=F(78); ruby_font=F(30)
      widths=[d.textbbox((0,0),x['base'],font=main_font)[2] for x in ruby]; gap=12; total=sum(widths)+gap*(len(widths)-1); x=(W-total)/2
      for item,w in zip(ruby,widths):
        d.text((x,360),item['base'],font=main_font,fill='white')
        if has_kanji(item['base']):
          r=hira(item['reading']); d.text((x,320),r,font=ruby_font,fill=(235,245,255,235))
        r=item['romaji']; box=d.textbbox((0,0),r,font=F(34)); d.text((x+(w-(box[2]-box[0]))/2,485),r,font=F(34),fill=(240,245,250,240))
        x+=w+gap
      center(d,595,cap['translationZh'],F(46),(245,245,245,230))
      cards=fr['grammarCards']; n=max(1,len(cards)); gap=12; total=1740; widths=[total//n]*n; widths[-1]+=total-sum(widths); x=90
      for card,w in zip(cards,widths):
        d.rounded_rectangle((x,705,x+w-gap,950),20,fill=(15,55,95,185),outline=(220,240,255,120),width=2)
        centerx=x+(w-gap)/2
        for y,text,size in [(730,card['token'],34),(795,card.get('functionZh',card['zhMeaning']),24),(855,card['posZh'],23)]:
          b=d.textbbox((0,0),text,font=F(size)); d.text((centerx-(b[2]-b[0])/2,y),text,font=F(size),fill='white')
        x+=w
    im.save(FR/f'{i:03d}.png')
if '--frames-only' in sys.argv:
    print(FR)
    raise SystemExit(0)
concat=OUT/'love2000.concat.txt'
lines=[]
for i,fr in enumerate(data['frames']):
    dur=(fr['endMs']-fr['startMs'])/1000; lines += [f"file '{(FR/f'{i:03d}.png').as_posix()}'",f'duration {dur:.3f}']
lines.append(f"file '{(FR/f'{len(data['frames'])-1:03d}.png').as_posix()}'"); concat.write_text('\n'.join(lines),encoding='utf8')
target = OUT / 'love2000-jlpt-2k.mp4'
subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-i',data['project']['audio'],'-vf','scale=2560:1440:flags=lanczos','-c:v','libx264','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-shortest',str(target)],check=True)
print(target)
