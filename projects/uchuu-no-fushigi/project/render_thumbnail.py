"""Reusable 16:9 and 4:3 cover renderer for the Japanese-song study series."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
FONT = 'C:/Windows/Fonts/msyh.ttc'

def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)

def text(draw, xy, value, size, color, bold=False):
    draw.text(xy, value, font=font(size, bold), fill=color)

def artwork_layer(art_path, side, h):
    """Fill the full left field with the square cover; crop horizontally, never pad."""
    art = Image.open(art_path).convert('RGB').resize((h, h), Image.Resampling.LANCZOS)
    left = (h - side) // 2
    return art.crop((left, 0, left + side, h))

def make_cover(art_path, song, artist, source, out_path):
    w, h, left = 1920, 1080, 840
    im = Image.new('RGB', (w, h), '#F6F4EE')
    im.paste(artwork_layer(art_path, left, h), (0, 0))
    d = ImageDraw.Draw(im)
    blue, navy, muted = '#D02640', '#3A1420', '#7A5660'
    d.rectangle((left, 0, left + 12, h), fill=blue)
    d.line((930, 155, 1770, 155), fill=blue, width=8)
    text(d, (920, 195), '快速学唱', 92, blue, True)
    text(d, (915, 335), song, 145, navy, True)
    text(d, (920, 560), artist, 54, navy, True)
    text(d, (920, 640), source, 40, muted)
    # The four study cues need to survive a small mobile thumbnail.
    text(d, (920, 800), '歌词 · 假名 · 罗马音', 54, navy, True)
    text(d, (920, 875), '逐词拆解', 70, navy, True)
    d.rectangle((920, 980, 1140, 990), fill=blue)
    im.save(out_path, quality=95)

def make_cover_4x3(art_path, song, artist, source, out_path):
    w, h, left = 1440, 1080, 630
    im = Image.new('RGB', (w, h), '#F6F4EE')
    im.paste(artwork_layer(art_path, left, h), (0, 0))
    d = ImageDraw.Draw(im)
    blue, navy, muted = '#D02640', '#3A1420', '#7A5660'
    d.rectangle((left, 0, left + 10, h), fill=blue)
    d.line((710, 165, 1350, 165), fill=blue, width=7)
    text(d, (700, 205), '快速学唱', 72, blue, True)
    text(d, (700, 325), song, 108, navy, True)
    text(d, (700, 505), artist, 44, navy, True)
    text(d, (700, 575), source, 32, muted)
    text(d, (700, 765), '歌词 · 假名', 45, navy, True)
    text(d, (700, 825), '罗马音 · 逐词拆解', 45, navy, True)
    d.rectangle((700, 925, 885, 934), fill=blue)
    im.save(out_path, quality=95)

if __name__ == '__main__':
    out = ROOT / 'output' / 'love2000-thumbnail.png'
    four_three = ROOT / 'output' / 'love2000-thumbnail-4x3.png'
    out.parent.mkdir(exist_ok=True)
    params = (ROOT / 'love2000-cover.jpg', 'LOVE 2000', '遠野ひかる', '败犬女主太多了 ED')
    make_cover(*params, out)
    make_cover_4x3(*params, four_three)
    print(out)
    print(four_three)
