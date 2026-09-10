from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\project\musicjlpt\projects\uchuu-no-fushigi-v2")
SOURCE = ROOT / "source" / "cover.jpg"
OUT = ROOT / "deliverables" / "final"
TEMPLATE = ROOT / "project" / "templates" / "cover.json"

def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

def font(path, size):
    return ImageFont.truetype(path, size)

def render(name, title, artist, subtitle, variant=None):
    spec = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    if variant:
        selected = spec["variants"][variant]
        spec = {**spec, "canvas": selected["canvas"], "artwork": selected["artwork"], "content": selected["content"]}
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    palette, content, artwork = spec["palette"], spec["content"], spec["artwork"]
    if len(title.splitlines()) != content["title"]["lines"]:
        raise ValueError("Song title must use the template's two fixed lines")
    image = Image.new("RGB", (width, height), rgb(palette["page"]))
    ax, ay, aw, ah = artwork["rectPx"]
    source = Image.open(SOURCE).convert("RGB")
    scale = max(aw / source.width, ah / source.height)
    resized = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    cx, cy = (resized.width - aw) // 2, (resized.height - ah) // 2
    image.paste(resized.crop((cx, cy, cx + aw, cy + ah)), (ax, ay))
    draw = ImageDraw.Draw(image)
    accent, ink, muted, rule = (rgb(palette[key]) for key in ("accent", "ink", "muted", "rule"))
    draw.rectangle((ax + aw, 0, ax + aw + artwork["separatorPx"], height), fill=accent)
    draw.line((content["leftPx"], content["topRuleY"], content["rightPx"], content["topRuleY"]), fill=rule, width=12)
    values = [("heading", content["heading"]["text"], accent), ("title", title, ink), ("artist", artist, muted), ("subtitle", subtitle, ink)]
    for key, value, color in values:
        block = content[key]
        draw.multiline_text((block["x"], block["y"]), value, font=font(spec["font"]["path"], block["fontSize"]), fill=color, spacing=4)
    features = content["features"]
    for value, y, size in zip(features["lines"], features["y"], features["fontSize"]):
        draw.text((features["x"], y), value, font=font(spec["font"]["path"], size), fill=ink)
    bottom = content["bottomRule"]
    draw.rectangle((bottom["x"], bottom["y"], bottom["x"] + bottom["width"], bottom["y"] + bottom["height"]), fill=rule)
    image.save(OUT / name, quality=95)

OUT.mkdir(parents=True, exist_ok=True)
render("uchuu-no-fushigi-v2--cover--16x9.png", "宇宙的\n不可思议", "夢限大みゅーたいぷ", "BanG Dream! YUME∞MITA ED")
render("uchuu-no-fushigi-v2--cover--4x3.png", "宇宙的\n不可思议", "夢限大みゅーたいぷ", "BanG Dream! YUME∞MITA ED", "4x3")
