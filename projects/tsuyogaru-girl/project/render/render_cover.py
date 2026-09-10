"""Render mobile-first platform covers from the frozen cover and current magic palette."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
SOURCE, PROJECT, FINAL = ROOT / "source", ROOT / "project", ROOT / "deliverables" / "final"
FONT = "C:/Windows/Fonts/msyhbd.ttc"


def font(size):
    return ImageFont.truetype(FONT, size)


def width(draw, text, selected):
    return draw.textbbox((0, 0), text, font=selected)[2]


def fitted(draw, text, start, max_width, minimum=28):
    for size in range(start, minimum - 1, -2):
        selected = font(size)
        if width(draw, text, selected) <= max_width:
            return selected
    raise ValueError(f"cover text cannot fit: {text}")


def crop_cover(width_px, height_px):
    source = Image.open(SOURCE / "cover.jpg").convert("RGB")
    scale = max(width_px / source.width, height_px / source.height)
    image = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    left, top = (image.width - width_px) // 2, (image.height - height_px) // 2
    return image.crop((left, top, left + width_px, top + height_px))


def render(name, canvas_width, artwork_width, config, palette):
    height = 1080
    page, accent = "#F5F2FF", palette["accent"]
    ink, muted = "#27203F", "#564A78"
    image = Image.new("RGB", (canvas_width, height), page)
    image.paste(crop_cover(artwork_width, height), (0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((artwork_width, 0, artwork_width + 12, height), fill=accent)
    left, right = artwork_width + 26, canvas_width - 18
    copy = config["copy"]
    draw.line((left, 76, right, 76), fill=accent, width=13)
    draw.text((left, 118), copy["heading"], font=font(112 if canvas_width == 1920 else 94), fill=accent)
    title_font = fitted(draw, copy["title"], 126 if canvas_width == 1920 else 98, right - left)
    draw.text((left - 4, 268), copy["title"], font=title_font, fill=ink)
    artist_font = fitted(draw, copy["artist"], 54 if canvas_width == 1920 else 44, right - left)
    draw.text((left, 515), copy["artist"], font=artist_font, fill=ink)
    subtitle_font = fitted(draw, copy["subtitle"], 58 if canvas_width == 1920 else 48, right - left)
    draw.text((left, 603), copy["subtitle"], font=subtitle_font, fill=muted)
    feature1, feature2 = copy["features"]
    draw.text((left, 756), feature1, font=fitted(draw, feature1, 77 if canvas_width == 1920 else 63, right - left), fill=ink)
    draw.text((left, 850), feature2, font=fitted(draw, feature2, 75 if canvas_width == 1920 else 63, right - left), fill=ink)
    draw.rectangle((left, 995, left + (390 if canvas_width == 1920 else 310), 1009), fill=accent)
    output = FINAL / f"tsuyogaru-girl--cover--{name}--20260818-r02.png"
    image.save(output, quality=96)
    return output


def main():
    config = json.loads((PROJECT / "templates" / "cover.json").read_text(encoding="utf-8"))
    palette = json.loads((PROJECT / "palette.json").read_text(encoding="utf-8"))
    FINAL.mkdir(parents=True, exist_ok=True)
    outputs = [render("16x9", 1920, 820, config, palette), render("4x3", 1440, 600, config, palette)]
    (PROJECT / "qa" / "cover-report.json").write_text(json.dumps({"status": "passed", "template": "project/templates/cover.json", "font": FONT, "outputs": [str(path.relative_to(ROOT)) for path in outputs]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
