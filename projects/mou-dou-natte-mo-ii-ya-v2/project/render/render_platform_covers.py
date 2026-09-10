from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "source" / "cover.jpg"
OUT = ROOT.parent / "deliverables" / "final"
TEMPLATE = ROOT / "templates" / "cover.json"


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def font(path, size):
    return ImageFont.truetype(path, size)


def cover(name, title, artist, subtitle, variant=None):
    spec = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    if variant:
        selected = spec["variants"][variant]
        spec = {**spec, "canvas": selected["canvas"], "artwork": selected["artwork"], "content": selected["content"]}
    width, height = spec["canvas"]["width"], spec["canvas"]["height"]
    palette, content, artwork = spec["palette"], spec["content"], spec["artwork"]
    if len(title.splitlines()) != content["title"].get("lines", 2):
        raise ValueError("The cover title must occupy exactly the template's two fixed lines")
    image = Image.new("RGB", (width, height), rgb(palette["page"]))
    ax, ay, aw, ah = artwork["rectPx"]
    source = Image.open(SOURCE).convert("RGB")
    scaled = source.resize((ah, ah), Image.Resampling.LANCZOS)
    crop_x = (ah - aw) // 2
    image.paste(scaled.crop((crop_x, 0, crop_x + aw, ah)), (ax, ay))
    draw = ImageDraw.Draw(image)
    accent, ink, muted, rule = (rgb(palette[key]) for key in ("accent", "ink", "muted", "rule"))
    draw.rectangle((ax + aw, 0, ax + aw + artwork["separatorPx"], height), fill=accent)
    draw.line((content["leftPx"], content["topRuleY"], content["rightPx"], content["topRuleY"]), fill=rule, width=12)
    font_path = spec["font"]["path"]
    for key, value, color in (("heading", content["heading"]["text"], accent), ("title", title, ink), ("artist", artist, muted), ("subtitle", subtitle, ink)):
        block = content[key]
        draw.text((block["x"], block["y"]), value, font=font(font_path, block["fontSize"]), fill=color)
    features = content["features"]
    for value, y, size in zip(features["lines"], features["y"], features["fontSize"]):
        draw.text((features["x"], y), value, font=font(font_path, size), fill=ink)
    bottom = content["bottomRule"]
    draw.rectangle((bottom["x"], bottom["y"], bottom["x"] + bottom["width"], bottom["y"] + bottom["height"]), fill=rule)
    image.save(OUT / name, quality=95)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    cover("mou-dou-natte-mo-ii-ya-v2--cover--16x9.png", "もうどうなっても\nいいや", "星街すいせい", "GQuuuuuuX ED")
    cover("mou-dou-natte-mo-ii-ya-v2--cover--4x3.png", "もうどうなっても\nいいや", "星街すいせい", "GQuuuuuuX ED", "4x3")
