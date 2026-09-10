"""Static composition preview: Gaussian cover background + low cover-wave + learning foreground."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

ROOT = Path(__file__).parent
SOURCE, OUT = ROOT.parent / "source", ROOT.parent / "deliverables"
W, H = 1920, 1080
FONT = "C:/Windows/Fonts/msyhbd.ttc"
ACCENT, ACTIVE, CARD = (215, 28, 55), (255, 112, 135), (103, 10, 30, 190)
def f(size): return ImageFont.truetype(FONT, size)
def center(draw, y, text, font, fill):
    box=draw.textbbox((0,0),text,font=font); draw.text(((W-(box[2]-box[0]))/2,y),text,font=font,fill=fill)

cover=Image.open(SOURCE/'COVER.jpg').convert('RGB')
background=cover.resize((W,H),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30)).convert('RGBA')
image=Image.alpha_composite(background,Image.new('RGBA',(W,H),(0,0,0,125)))
draw=ImageDraw.Draw(image,'RGBA')

# The waveform intentionally stays beneath all study content.
base=1015
for i in range(112):
    x=45+i*16
    energy=18+int(55*((math.sin(i*.47)+1)/2))+int(30*((math.sin(i*.16+1)+1)/2))
    draw.rounded_rectangle((x,base-energy,x+8,base+energy),4,fill=ACCENT+(170,))
draw.line((36,base,1884,base),fill=ACTIVE+(160,),width=2)

# Existing series foreground: a small cover on top, full-frame lyric veil, no opaque reading panel.
veil=Image.new('RGBA',(W,H),(0,0,0,74))
image=Image.alpha_composite(image,veil)
small=cover.resize((220,220),Image.Resampling.LANCZOS)
image.alpha_composite(small.convert('RGBA'),(850,35))
draw=ImageDraw.Draw(image,'RGBA')
tokens=[('夢','ゆめ','yume','梦','名词'),('を','','wo','动作对象','助词'),('醒ます','さます','samasu','唤醒','动词'),('朝','あさ','asa','清晨','名词'),('の','','no','所属修饰','助词'),('光','ひかり','hikari','光芒','名词')]
widths=[draw.textbbox((0,0),t[0],font=f(80))[2] for t in tokens]; x=(W-sum(widths)-18*(len(tokens)-1))/2
for index,(token,ruby,roma,meaning,pos) in enumerate(tokens):
    width=widths[index]; color=ACTIVE if index==2 else 'white'
    if ruby: draw.text((x,330),ruby,font=f(30),fill=color)
    draw.text((x,370),token,font=f(80),fill=color)
    box=draw.textbbox((0,0),roma,font=f(38)); draw.text((x+(width-(box[2]-box[0]))/2,475),roma,font=f(38),fill=color)
    x+=width+18
center(draw,555,'清晨的阳光，将梦唤醒。',f(48),(245,245,245,240))
gap,x,total=12,95,1730; cardw=total//len(tokens)
for token,ruby,roma,meaning,pos in tokens:
    draw.rounded_rectangle((x,665,x+cardw-gap,900),20,fill=CARD,outline=ACTIVE+(150,),width=2)
    box=draw.textbbox((0,0),token,font=f(38)); draw.text((x+(cardw-gap-(box[2]-box[0]))/2,690),token,font=f(38),fill='white')
    box=draw.textbbox((0,0),meaning,font=f(27)); draw.text((x+(cardw-gap-(box[2]-box[0]))/2,758),meaning,font=f(27),fill='white')
    box=draw.textbbox((0,0),pos,font=f(26)); draw.text((x+(cardw-gap-(box[2]-box[0]))/2,828),pos,font=f(26),fill='white')
    x+=cardw
image.convert('RGB').save(OUT/'brand-new-days-cover-wave-foreground-preview.png',quality=95)
