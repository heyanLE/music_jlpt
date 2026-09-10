"""Reusable 16:9 and 4:3 cover renderer for the Japanese-song study series."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
FONT = 'C:/Windows/Fonts/msyhbd.ttc'

def font(size, bold=False):
    return ImageFont.truetype(FONT, size)

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
    blue, navy, muted = '#3EB9FF', '#102B42', '#526F84'
    d.rectangle((left, 0, left + 12, h), fill=blue)
    d.line((875, 110, 1900, 110), fill=blue, width=12)
    text(d, (865, 145), '快速学唱', 122, blue, True)
    text(d, (855, 300), song, 178, navy, True)
    text(d, (865, 540), artist, 68, navy, True)
    text(d, (865, 625), source, 50, muted, True)
    # Four explicit, scan-friendly learning cues for mobile thumbnails.
    text(d, (865, 770), '歌词同步高亮 · 假名', 62, navy, True)
    text(d, (865, 855), '罗马音 · 文法', 74, navy, True)
    d.rectangle((865, 990, 1170, 1004), fill=blue)
    im.save(out_path, quality=95)

def make_cover_4x3(art_path, song, artist, source, out_path):
    w, h, left = 1440, 1080, 630
    im = Image.new('RGB', (w, h), '#F6F4EE')
    im.paste(artwork_layer(art_path, left, h), (0, 0))
    d = ImageDraw.Draw(im)
    blue, navy, muted = '#3EB9FF', '#102B42', '#526F84'
    d.rectangle((left, 0, left + 10, h), fill=blue)
    d.line((650, 110, 1420, 110), fill=blue, width=11)
    text(d, (645, 145), '快速学唱', 95, blue, True)
    text(d, (635, 280), song, 132, navy, True)
    text(d, (645, 490), artist, 56, navy, True)
    text(d, (645, 565), source, 40, muted, True)
    text(d, (645, 760), '歌词同步高亮 · 假名', 54, navy, True)
    text(d, (645, 835), '罗马音 · 文法', 64, navy, True)
    d.rectangle((645, 955, 900, 968), fill=blue)
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
