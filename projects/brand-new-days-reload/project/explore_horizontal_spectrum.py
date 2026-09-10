"""Create static visual explorations for bottom horizontal spectrum styles."""
from math import sin, pi
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent
SOURCE = ROOT / 'check-v11-english.png'
OUT = ROOT / 'horizontal-spectrum-exploration'
OUT.mkdir(exist_ok=True)
W, H = 1920, 1080
ACCENT = (215, 28, 55)
LIGHT = (255, 108, 127)

def panel(image):
    layer = Image.new('RGBA', (W, 180), (3, 4, 8, 218))
    image.alpha_composite(layer, (0, 900))
    return ImageDraw.Draw(image, 'RGBA')

def label(draw, text):
    draw.text((58, 918), text, fill=(255, 255, 255, 190), stroke_width=1, stroke_fill=(0, 0, 0, 160))

def values(count):
    return [0.24 + 0.60 * ((sin(i * 0.53) + 1) / 2) * (0.70 + 0.30 * ((sin(i * 0.17 + 1.2) + 1) / 2)) for i in range(count)]

def soft_capsules(image):
    draw = panel(image); label(draw, 'A  SOFT CAPSULES')
    vals = values(72); gap = 10; width = (W - 116 - gap * (len(vals) - 1)) // len(vals)
    glow = Image.new('RGBA', (W, 180), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow, 'RGBA')
    for i, value in enumerate(vals):
        height = int(24 + 94 * value); x = 58 + i * (width + gap)
        gd.rounded_rectangle((x, 105 + (150-height)/2, x+width, 105 + (150+height)/2), radius=width//2, fill=ACCENT+(105,))
    glow = glow.filter(ImageFilter.GaussianBlur(13)); image.alpha_composite(glow, (0, 900))
    for i, value in enumerate(vals):
        height = int(24 + 94 * value); x = 58 + i * (width + gap)
        draw.rounded_rectangle((x, 105 + (150-height)/2, x+width, 105 + (150+height)/2), radius=width//2, fill=ACCENT+(230,))
        draw.line((x+width//2, 105+(150-height)/2+4, x+width//2, 105+(150+height)/2-4), fill=LIGHT+(185,), width=2)

def split_equalizer(image):
    draw = panel(image); label(draw, 'B  SPLIT EQUALIZER')
    vals = values(48); gap = 16; width = (W - 140 - gap * (len(vals) - 1)) // len(vals); mid = 990
    draw.line((54, mid, W-54, mid), fill=(255,255,255,38), width=1)
    for i, value in enumerate(vals):
        height = int(18 + 61 * value); x = 70 + i * (width + gap)
        draw.rounded_rectangle((x, mid-height-5, x+width, mid-5), radius=4, fill=ACCENT+(220,))
        draw.rounded_rectangle((x, mid+5, x+width, mid+height+5), radius=4, fill=LIGHT+(170,))

def horizon_line(image):
    draw = panel(image); label(draw, 'C  HORIZON PULSE')
    y = 992; points = []
    for x in range(56, W-56, 6):
        p = (x-56)/(W-112)
        amp = 20 + 45 * (0.35 + 0.65*((sin(p*22*pi)+1)/2)) * (0.55+0.45*sin(p*4*pi+0.5)**2)
        points.append((x, y - amp * sin(p*33*pi)))
    glow = Image.new('RGBA', (W,180), (0,0,0,0)); gd=ImageDraw.Draw(glow,'RGBA'); gd.line([(x,y2-900) for x,y2 in points], fill=ACCENT+(190,), width=12, joint='curve')
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)), (0,900))
    draw.line(points, fill=LIGHT+(230,), width=4, joint='curve')
    for x, y2 in points[::18]: draw.ellipse((x-3,y2-3,x+3,y2+3),fill=(255,255,255,185))

def stepped_meter(image):
    draw = panel(image); label(draw, 'D  STEPPED METER')
    vals = values(64); gap = 8; width = (W-116-gap*(len(vals)-1))//len(vals); base=1058
    for i,value in enumerate(vals):
        x=58+i*(width+gap); steps=max(2,int(2+7*value))
        for step in range(steps):
            y=base-step*17
            color=LIGHT+(225,) if step==steps-1 else ACCENT+(185,)
            draw.rounded_rectangle((x,y-11,x+width,y),radius=3,fill=color)

styles = [('a-soft-capsules', soft_capsules), ('b-split-equalizer', split_equalizer), ('c-horizon-pulse', horizon_line), ('d-stepped-meter', stepped_meter)]
previews=[]
for name, painter in styles:
    image=Image.open(SOURCE).convert('RGBA'); painter(image); target=OUT/f'{name}.png'; image.convert('RGB').save(target, quality=95); previews.append(target)
sheet=Image.new('RGB',(960,1080),(12,12,16))
for index,path in enumerate(previews):
    item=Image.open(path).convert('RGB').resize((480,270),Image.Resampling.LANCZOS)
    sheet.paste(item,((index%2)*480,(index//2)*270))
sheet.save(OUT/'contact-sheet.png',quality=95)
print(OUT/'contact-sheet.png')
