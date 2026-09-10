from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT, OUT = Path(__file__).parent, Path(__file__).parent.parent / "deliverables"
FONT, ACCENT, INK, MUTED = "C:/Windows/Fonts/msyhbd.ttc", "#E13D68", "#4E1827", "#854456"
def F(size): return ImageFont.truetype(FONT, size)
def put(draw, xy, value, size, color): draw.text(xy, value, font=F(size), fill=color)
def art(width, height):
    image = Image.open(ROOT.parent / "source" / "COVER.jpg").convert("RGB").resize((height, height), Image.Resampling.LANCZOS)
    left = (height - width) // 2; return image.crop((left, 0, left + width, height))
def cover(width, left, path):
    height = 1080; image = Image.new("RGB", (width, height), "#FFF5F7"); image.paste(art(left, height), (0, 0)); draw = ImageDraw.Draw(image)
    draw.rectangle((left, 0, left + 12, height), fill=ACCENT); x = left + 25; draw.line((x, 110, width - 20, 110), fill=ACCENT, width=12)
    put(draw, (x, 145), "快速学唱", 118 if width == 1920 else 92, ACCENT); put(draw, (x - 5, 300), "HALO", 160 if width == 1920 else 122, INK)
    put(draw, (x, 530), "NOMELON NOLEMON", 60 if width == 1920 else 45, INK); put(draw, (x, 615), "机动战士Gundam GQuuuuuuX 插曲", 39 if width == 1920 else 29, MUTED)
    put(draw, (x, 770), "歌词同步高亮 · 假名", 62 if width == 1920 else 53, INK); put(draw, (x, 855), "罗马音 · 文法", 76 if width == 1920 else 64, INK)
    draw.rectangle((x, 990 if width == 1920 else 955, x + 300, 1004 if width == 1920 else 968), fill=ACCENT); image.save(path, quality=95)
cover(1920, 840, OUT / "halo-thumbnail-v1.png")
cover(1440, 630, OUT / "halo-thumbnail-4x3-v1.png")

def vertical_cover(path):
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), "#FFF5F7")
    square = Image.open(ROOT.parent / "source" / "COVER.jpg").convert("RGB").resize((1080, 1080), Image.Resampling.LANCZOS)
    image.paste(square, (0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1065, width, 1080), fill=ACCENT)
    x = 56
    put(draw, (x, 1130), "\u5feb\u901f\u5b66\u5531", 108, ACCENT)
    put(draw, (x, 1275), "HALO", 180, INK)
    put(draw, (x, 1485), "NOMELON NOLEMON", 62, INK)
    put(draw, (x, 1575), "\u673a\u52a8\u6218\u58eb Gundam GQuuuuuuX \u63d2\u66f2", 35, MUTED)
    put(draw, (x, 1690), "\u6b4c\u8bcd\u540c\u6b65\u9ad8\u4eae \u00b7 \u5047\u540d", 58, INK)
    put(draw, (x, 1770), "\u7f57\u9a6c\u97f3 \u00b7 \u6587\u6cd5", 68, INK)
    draw.rectangle((x, 1860, x + 360, 1876), fill=ACCENT)
    image.save(path, quality=95)

vertical_cover(OUT / "halo-thumbnail-9x16-v1.png")

def portrait_3x4(path):
    width, height = 1440, 1920
    image = Image.new("RGB", (width, height), "#FFF5F7")
    square = Image.open(ROOT.parent / "source" / "COVER.jpg").convert("RGB").resize((1120, 1120), Image.Resampling.LANCZOS)
    image.paste(square, (160, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 1100, width, 1118), fill=ACCENT)
    x = 84
    put(draw, (x, 1165), "\u5feb\u901f\u5b66\u5531", 120, ACCENT)
    put(draw, (x, 1315), "HALO", 200, INK)
    put(draw, (x, 1540), "NOMELON NOLEMON", 72, INK)
    put(draw, (x, 1635), "\u673a\u52a8\u6218\u58eb Gundam GQuuuuuuX \u63d2\u66f2", 41, MUTED)
    put(draw, (x, 1745), "\u6b4c\u8bcd\u540c\u6b65\u9ad8\u4eae \u00b7 \u5047\u540d", 62, INK)
    put(draw, (x, 1825), "\u7f57\u9a6c\u97f3 \u00b7 \u6587\u6cd5", 74, INK)
    draw.rectangle((x, 1900, x + 390, 1917), fill=ACCENT)
    image.save(path, quality=95)

portrait_3x4(OUT / "halo-thumbnail-3x4-v1.png")
