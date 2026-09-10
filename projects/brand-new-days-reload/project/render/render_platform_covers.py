from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(r"C:\project\musicjlpt\projects\brand-new-days-reload")
SOURCE = ROOT / "source" / "COVER.jpg"
OUT = ROOT / "deliverables" / "final"
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
ACCENT = (215, 28, 55)
INK = (18, 11, 14)
WHITE = (255, 255, 255)
TITLE = "Brand New Days\n-Reload-"
ARTIST = "高橋あず美 & アトラスサウンドチーム"
BENEFITS = ["歌词同步高亮", "假名注释", "罗马音", "逐词拆解"]


def font(size):
    return ImageFont.truetype(FONT, size, index=0)


def fit(image, box):
    x, y, width, height = box
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height)), (x, y)


def text(draw, xy, value, size, fill=WHITE, spacing=10, anchor=None, stroke=0):
    draw.multiline_text(xy, value, font=font(size), fill=fill, spacing=spacing, anchor=anchor,
                        stroke_width=stroke, stroke_fill=INK)


def panel(canvas, rect):
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle(rect, radius=26, fill=(255, 255, 255, 24), outline=(255, 255, 255, 80), width=2)


def render_landscape(name, width, height):
    art_width = round(width * 0.57)
    art = Image.open(SOURCE).convert("RGB")
    bg = art.resize((width, height), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(38)).convert("RGBA")
    shade = Image.new("RGBA", (width, height), (*INK, 215)); bg.alpha_composite(shade)
    art_crop, pos = fit(art, (0, 0, art_width, height)); bg.alpha_composite(art_crop.convert("RGBA"), pos)
    draw = ImageDraw.Draw(bg, "RGBA")
    draw.rectangle((art_width - 8, 0, art_width + 12, height), fill=ACCENT + (255,))
    x = art_width + round(width * 0.045)
    text(draw, (x, round(height * .105)), "快速学唱", round(height * .10), fill=ACCENT, stroke=2)
    text(draw, (x, round(height * .245)), TITLE, round(height * .073), spacing=8, stroke=2)
    text(draw, (x, round(height * .485)), ARTIST, round(height * .035), fill=(235, 235, 235), stroke=1)
    bottom = round(height * .63)
    for i, benefit in enumerate(BENEFITS):
        yy = bottom + i * round(height * .075)
        text(draw, (x, yy), f"• {benefit}", round(height * .040), fill=WHITE, stroke=1)
    bg.convert("RGB").save(OUT / name, quality=95)


def render_portrait(name, width, height):
    art = Image.open(SOURCE).convert("RGB")
    bg = art.resize((width, height), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(42)).convert("RGBA")
    bg.alpha_composite(Image.new("RGBA", (width, height), (*INK, 205)))
    art_height = round(height * .44)
    art_crop, pos = fit(art, (0, 0, width, art_height)); bg.alpha_composite(art_crop.convert("RGBA"), pos)
    draw = ImageDraw.Draw(bg, "RGBA")
    draw.rectangle((0, art_height - 8, width, art_height + 12), fill=ACCENT + (255,))
    margin = round(width * .075)
    text(draw, (margin, art_height + round(height * .045)), "快速学唱", round(width * .11), fill=ACCENT, stroke=2)
    text(draw, (margin, art_height + round(height * .125)), TITLE, round(width * .072), spacing=8, stroke=2)
    text(draw, (margin, art_height + round(height * .265)), ARTIST, round(width * .037), fill=(235,235,235), stroke=1)
    y = art_height + round(height * .34)
    for i, benefit in enumerate(BENEFITS):
        yy = y + i * round(height * .052)
        panel(bg, (margin, yy - 10, width - margin, yy + round(height * .048)))
        text(draw, (margin + 22, yy), benefit, round(width * .052), fill=WHITE, stroke=1)
    bg.convert("RGB").save(OUT / name, quality=95)


OUT.mkdir(parents=True, exist_ok=True)
render_landscape("brand-new-days-reload--cover-16x9--20260819.png", 1920, 1080)
render_landscape("brand-new-days-reload--cover-4x3--20260819.png", 1440, 1080)
render_portrait("brand-new-days-reload--cover-9x16--20260819.png", 1080, 1920)
render_portrait("brand-new-days-reload--cover-3x4--20260819.png", 1440, 1920)
