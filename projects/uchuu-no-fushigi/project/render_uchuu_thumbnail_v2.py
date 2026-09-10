"""Create phone-first 16:9 and 4:3 covers using the art's lavender magic colour."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
OUT = ROOT.parent / "deliverables"
FONT = "C:/Windows/Fonts/msyhbd.ttc"
ACCENT, INK, MUTED = "#D8A9F2", "#251A3C", "#604F70"


def F(size):
    return ImageFont.truetype(FONT, size)


def put(draw, xy, value, size, color):
    draw.text(xy, value, font=F(size), fill=color)


def artwork(width, height):
    image = Image.open(ROOT / "uchuu-cover.jpg").convert("RGB").resize((height, height), Image.Resampling.LANCZOS)
    left = (height - width) // 2
    return image.crop((left, 0, left + width, height))


def cover(width, left, path):
    height = 1080
    image = Image.new("RGB", (width, height), "#F8F4FB")
    image.paste(artwork(left, height), (0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((left, 0, left + 12, height), fill=ACCENT)
    x = left + 25
    draw.line((x, 110, width - 20, 110), fill=ACCENT, width=12)
    put(draw, (x, 145), "快速学唱", 118 if width == 1920 else 92, ACCENT)
    put(draw, (x - 5, 300), "うちゅうのふしぎ", 132 if width == 1920 else 100, INK)
    put(draw, (x, 530), "夢限大みゅーたいぷ", 64 if width == 1920 else 50, INK)
    put(draw, (x, 615), "BanG Dream! YUME∞MITA ED", 45 if width == 1920 else 34, MUTED)
    put(draw, (x, 770), "歌词同步高亮 · 假名", 62 if width == 1920 else 53, INK)
    put(draw, (x, 855), "罗马音 · 文法", 76 if width == 1920 else 64, INK)
    draw.rectangle((x, 990 if width == 1920 else 955, x + 300, 1004 if width == 1920 else 968), fill=ACCENT)
    image.save(path, quality=95)


cover(1920, 840, OUT / "uchuu-thumbnail-v2.png")
cover(1440, 630, OUT / "uchuu-thumbnail-4x3-v2.png")
print(OUT / "uchuu-thumbnail-v2.png")
print(OUT / "uchuu-thumbnail-4x3-v2.png")
