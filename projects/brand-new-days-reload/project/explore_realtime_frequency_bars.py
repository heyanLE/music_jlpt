"""Create design previews for real-time horizontal frequency columns."""
from math import sin, pi
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).parent
# Use the clean blurred-cover background: do not inherit the old visualizer's
# opaque band when reviewing the next background treatment.
SOURCE=ROOT/'cover_wave_background.png'
OUT=ROOT/'realtime-frequency-bars-exploration'
OUT.mkdir(exist_ok=True)
W,H=1920,1080
ACCENT=(215,28,55)
LIGHT=(255,112,135)

def mix(a,b,t): return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))
def levels(count):
    return [0.18+0.72*((sin(i*.43)+1)/2)*(.55+.45*((sin(i*.16+1.3)+1)/2)) for i in range(count)]
def base():
    return Image.open(SOURCE).convert('RGBA')
def title(d, text): d.text((58,918),text,fill=(255,255,255,180),stroke_width=1,stroke_fill=(0,0,0,150))

def soft_peak(image):
    d=ImageDraw.Draw(image,'RGBA'); title(d,'A  SOFT PEAK BARS')
    vals=levels(52); gap=15; width=(W-116-gap*(len(vals)-1))//len(vals); glow=Image.new('RGBA',(W,180),(0,0,0,0)); gd=ImageDraw.Draw(glow,'RGBA')
    for i,v in enumerate(vals):
        x=58+i*(width+gap); h=int(25+102*v); color=mix(ACCENT,LIGHT,i/(len(vals)-1))
        gd.rounded_rectangle((x,105+150-h,x+width,105+150),radius=width//2,fill=color+(130,))
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)),(0,900))
    for i,v in enumerate(vals):
        x=58+i*(width+gap); h=int(25+102*v); color=mix(ACCENT,LIGHT,i/(len(vals)-1))
        d.rounded_rectangle((x,105+150-h,x+width,105+150),radius=width//2,fill=color+(235,))
        d.rounded_rectangle((x-2,101+150-h,x+width+2,105+150-h),radius=2,fill=(255,220,225,230))

def glass_stems(image):
    d=ImageDraw.Draw(image,'RGBA'); title(d,'B  GLASS STEMS')
    vals=levels(64); gap=11; width=(W-116-gap*(len(vals)-1))//len(vals); y=1060
    d.line((58,y,W-58,y),fill=(255,255,255,45),width=1)
    for i,v in enumerate(vals):
        x=58+i*(width+gap); h=int(20+105*v); color=mix((145,17,38),LIGHT,i/(len(vals)-1))
        d.rounded_rectangle((x,y-h,x+width,y),radius=width//2,fill=color+(145,))
        d.rounded_rectangle((x-1,y-h-4,x+width+1,y-h+2),radius=3,fill=LIGHT+(245,))

def mirrored_capsules(image):
    d=ImageDraw.Draw(image,'RGBA'); title(d,'C  MIRRORED CAPSULES')
    vals=levels(48); gap=18; width=(W-116-gap*(len(vals)-1))//len(vals); mid=997
    d.line((58,mid,W-58,mid),fill=LIGHT+(80,),width=2)
    for i,v in enumerate(vals):
        x=58+i*(width+gap); h=int(15+58*v); color=mix(ACCENT,LIGHT,i/(len(vals)-1))
        d.rounded_rectangle((x,mid-h-5,x+width,mid-5),radius=width//2,fill=color+(235,))
        d.rounded_rectangle((x,mid+5,x+width,mid+h+5),radius=width//2,fill=color+(105,))

def segmented_meter(image):
    d=ImageDraw.Draw(image,'RGBA'); title(d,'D  SEGMENTED METER')
    vals=levels(52); gap=14; width=(W-116-gap*(len(vals)-1))//len(vals); y=1060
    for i,v in enumerate(vals):
        x=58+i*(width+gap); steps=max(2,round(2+7*v)); color=mix(ACCENT,LIGHT,i/(len(vals)-1))
        for j in range(8):
            yy=y-j*17
            fill=color+(235,) if j<steps else (90,14,28,90)
            d.rounded_rectangle((x,yy-11,x+width,yy),radius=3,fill=fill)

styles=[('a-soft-peak-bars',soft_peak),('b-glass-stems',glass_stems),('c-mirrored-capsules',mirrored_capsules),('d-segmented-meter',segmented_meter)]
paths=[]
for name,painter in styles:
    image=base(); painter(image); path=OUT/f'{name}.png'; image.convert('RGB').save(path,quality=95); paths.append(path)
sheet=Image.new('RGB',(960,540),(8,9,13))
for index,path in enumerate(paths):
    item=Image.open(path).convert('RGB').resize((480,270),Image.Resampling.LANCZOS)
    sheet.paste(item,((index%2)*480,(index//2)*270))
sheet.save(OUT/'contact-sheet.png',quality=95)
print(OUT/'contact-sheet.png')
