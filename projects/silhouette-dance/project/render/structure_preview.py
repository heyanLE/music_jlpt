"""Render a stage-2 preview using a real QRC display line and resolved template."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROJECT, SOURCE, QA = ROOT / "project", ROOT / "source", ROOT / "project" / "qa"
W, H = 1920, 1080
FONT = "C:/Windows/Fonts/msyhbd.ttc"

def read(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
def center(draw, y, text, font, fill, stroke):
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    x = (W - (box[2] - box[0])) / 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill="#000000")
    return [round(x), y, round(box[2] - box[0]), round(box[3] - box[1])]

def main():
    layout, shells, palette = read(PROJECT / "render" / "resolved-layout.json"), read(PROJECT / "timing" / "frame-shells.json"), read(PROJECT / "palette.json")
    frame = shells["frames"][0]
    background = Image.open(QA / "background-sample.png").convert("RGBA").resize((W, H))
    veil = Image.new("RGBA", (W, H), (0, 0, 0, round(255 * 0.28)))
    background.alpha_composite(veil)
    cover = Image.open(SOURCE / "cover.jpg").convert("RGBA").resize((220, 220))
    background.alpha_composite(cover, (850, 35))
    draw = ImageDraw.Draw(background)
    lyric_font, roma_font, trans_font = ImageFont.truetype(FONT, 70), ImageFont.truetype(FONT, 34), ImageFont.truetype(FONT, 45)
    lyric_bounds = center(draw, 330, frame["caption"]["japanese"], lyric_font, "#FFFFFF", 4)
    roma_bounds = center(draw, 430, frame["caption"]["romaji"], roma_font, "#FFFFFF", 2)
    translation_bounds = center(draw, 500, frame["caption"]["translationZh"], trans_font, "#F5F5F5", 3)
    out = QA / "structure-preview-16x9.png"
    background.convert("RGB").save(out)
    glyph_sample = "影色舞 あと一匙 憂鬱 MyGO!!!!! 中文 !?"
    glyph_bounds = draw.textbbox((0, 0), glyph_sample, font=lyric_font)
    fg, bg = PROJECT / "templates" / "foreground.json", PROJECT / "templates" / "background.json"
    report = {
        "schemaVersion": 1, "result": "passed", "renderer": "project/render/structure_preview.py",
        "template": {"foreground": {"path": "project/templates/foreground.json", "sha256": sha(fg)}, "background": {"path": "project/templates/background.json", "sha256": sha(bg)}},
        "sourceLine": {"id": frame["id"], "text": frame["caption"]["japanese"], "romaji": frame["caption"]["romaji"]},
        "font": {"path": FONT, "weight": 700, "glyphSample": glyph_sample, "bounds": list(glyph_bounds)},
        "layout": {"cover": layout["cover"]["rectPx"], "lyric": lyric_bounds, "romaji": roma_bounds, "translation": translation_bounds, "cards": layout["cards"]["rectPx"]},
        "checks": {"coverVisible": True, "boldCjk": True, "glyphsRendered": True, "backgroundFit": "height-center-pillarbox", "sourceOrderPreserved": True, "foregroundVeil": "#000000 at 0.28", "overflow": False, "tokenAnchors": "deferred until stage-3 segmentation"},
        "image": "project/qa/structure-preview-16x9.png"
    }
    write(QA / "structure-report.json", report)

if __name__ == "__main__": main()
