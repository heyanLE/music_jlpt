"""Static composition preview: current learning foreground over cover-ring background."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
PROJECT, SOURCE, OUT = ROOT.parent, ROOT.parent / "source", ROOT.parent / "deliverables"
W, H = 1920, 1080
FONT = "C:/Windows/Fonts/msyhbd.ttc"
ACCENT, ACTIVE, CARD = (215, 28, 55), (255, 112, 135), (103, 10, 30, 190)

def f(size): return ImageFont.truetype(FONT, size)
def center(draw, y, text, font, fill):
    box=draw.textbbox((0,0),text,font=font); draw.text(((W-(box[2]-box[0]))/2,y),text,font=font,fill=fill)

cover=Image.open(SOURCE/'COVER.jpg').convert('RGB')
bg=cover.resize((W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(28)).convert('RGBA')
image=Image.alpha_composite(bg,Image.new('RGBA',(W,H),(0,0,0,106)))
draw=ImageDraw.Draw(image,'RGBA')
cx,cy=960,250
draw.ellipse((cx-210,cy-210,cx+210,cy+210),fill=(0,0,0,120),outline=ACCENT+(160,),width=3)
import math
for b in range(96):
    a=math.pi*2*b/96-math.pi/2; n=188+(b%7)*9
    draw.line((cx+math.cos(a)*180,cy+math.sin(a)*180,cx+math.cos(a)*n,cy+math.sin(a)*n),fill=ACCENT+(215,),width=5)
album=cover.resize((310,310),Image.Resampling.LANCZOS); image.alpha_composite(album.convert('RGBA'),(805,95))

# Learning foreground: it starts below the shifted spectrum, keeping both layers legible.
draw.rounded_rectangle((170,460,1750,1000),28,fill=(0,0,0,154))
tokens=[('夢','ゆめ','yume','梦','名词'),('を','','wo','动作对象','助词'),('醒ます','さます','samasu','唤醒','动词'),('朝','あさ','asa','清晨','名词'),('の','','no','所属修饰','助词'),('光','ひかり','hikari','光芒','名词')]
widths=[draw.textbbox((0,0),t[0],font=f(68))[2] for t in tokens]; x=(W-sum(widths)-14*(len(tokens)-1))/2
for idx,(token,ruby,roma,meaning,pos) in enumerate(tokens):
    width=widths[idx]; color=ACTIVE if idx==2 else 'white'
    if ruby: draw.text((x,497),ruby,font=f(27),fill=color)
    draw.text((x,535),token,font=f(68),fill=color)
    box=draw.textbbox((0,0),roma,font=f(32)); draw.text((x+(width-(box[2]-box[0]))/2,620),roma,font=f(32),fill=color)
    x+=width+14
center(draw,677,'清晨的阳光，将梦唤醒。',f(43),(245,245,245,240))
gap, x, total = 12, 102, 1716
cardw=total//len(tokens)
for token,ruby,roma,meaning,pos in tokens:
    draw.rounded_rectangle((x,745,x+cardw-gap,965),18,fill=CARD,outline=ACTIVE+(150,),width=2)
    box=draw.textbbox((0,0),token,font=f(34)); draw.text((x+(cardw-gap-(box[2]-box[0]))/2,767),token,font=f(34),fill='white')
    box=draw.textbbox((0,0),meaning,font=f(25)); draw.text((x+(cardw-gap-(box[2]-box[0]))/2,825),meaning,font=f(25),fill='white')
    box=draw.textbbox((0,0),pos,font=f(24)); draw.text((x+(cardw-gap-(box[2]-box[0]))/2,888),pos,font=f(24),fill='white')
    x+=cardw
image.convert('RGB').save(OUT/'brand-new-days-cover-ring-foreground-preview.png',quality=95)
