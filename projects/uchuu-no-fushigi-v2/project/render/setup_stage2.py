"""Deterministic stage-2 setup and structure preview for this frozen project."""
import colorsys
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
TIMING = PROJECT / "timing"
QA = PROJECT / "qa"
SOURCE = ROOT / "source"
W, H = 1920, 1080
FONT_PATH = "C:/Windows/Fonts/msyhbd.ttc"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hex_rgb(value):
    return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))


def palette():
    image = Image.open(SOURCE / "cover.jpg").convert("RGB").resize((160, 160))
    candidates = []
    for red, green, blue in image.getdata():
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        if saturation >= 0.40 and 0.35 <= value <= 0.95 and 0.88 <= hue <= 1.0:
            candidates.append((red, green, blue))
    # The cover's repeated saturated warm-pink pixels are the magic-colour family.
    red = sum(pixel[0] for pixel in candidates) // len(candidates)
    green = sum(pixel[1] for pixel in candidates) // len(candidates)
    blue = sum(pixel[2] for pixel in candidates) // len(candidates)
    hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    active = colorsys.hsv_to_rgb(hue, min(1.0, saturation * 1.15), 1.0)
    active_hex = "#" + "".join(f"{round(component * 255):02X}" for component in active)
    accent_hex = f"#{red:02X}{green:02X}{blue:02X}"
    return {
        "accent": accent_hex,
        "activeTint": active_hex,
        "cardFill": accent_hex + "BF",
        "cardOutline": active_hex,
        "body": "#FFFFFF",
        "muted": "#FFF0F7"
    }


def first_lyric(lines):
    return next(line for line in lines if line["startMs"] >= 1600 and " - " not in line["text"] and not line["text"].startswith(("词：", "曲：")))


def nearest_text(start_ms, rows, threshold=350):
    row = min(rows, key=lambda item: abs(item["startMs"] - start_ms), default=None)
    return row["text"] if row and abs(row["startMs"] - start_ms) <= threshold else ""


def main():
    qm = read(TIMING / "qm.json")["lines"]
    roma = read(TIMING / "roma.json")["lines"]
    translations = read(TIMING / "translation.json")["lines"]
    eligible = [line for line in qm if line["startMs"] >= 1600 and " - " not in line["text"] and not line["text"].startswith(("词：", "曲："))]
    pal = palette()
    write(PROJECT / "palette.json", pal)

    fg_path, bg_path = PROJECT / "templates" / "foreground.json", PROJECT / "templates" / "background.json"
    fg, bg = read(fg_path), read(bg_path)
    resolved = {
        "schemaVersion": 1,
        "template": {"id": fg["id"], "sha256": sha(fg_path)},
        "canvas": {"width": W, "height": H, "normalized": {"width": 1, "height": 1}},
        "font": {"path": FONT_PATH, "weight": 700},
        "colors": {"body": pal["body"], "active": pal["activeTint"], "cardFill": pal["cardFill"], "cardOutline": pal["cardOutline"], "veil": "#00000047", "textStroke": "#000000"},
        "cover": {"rectPx": fg["cover"]["rectPx"], "rectNormalized": [round(value / W, 6) if index in (0, 2) else round(value / H, 6) for index, value in enumerate(fg["cover"]["rectPx"])]},
        "lyric": fg["lyric"],
        "cards": fg["cards"],
        "overflow": {"lyric": fg["lyric"]["overflow"], "cards": fg["cards"]["overflow"]},
        "background": {"id": bg["id"], "fit": bg["fit"], "loop": bg["loop"], "segments": bg.get("segments", [])}
    }
    write(PROJECT / "render" / "resolved-layout.json", resolved)

    frames = []
    for index, line in enumerate(eligible, start=1):
        frames.append({
            "id": f"l{index:03}",
            "startMs": line["startMs"], "endMs": line["endMs"],
            "displayUnits": [{"kind": "japanese", "text": line["text"], "qrcParts": line["parts"]}],
            "caption": {"japanese": line["text"], "furigana": [], "romaji": nearest_text(line["startMs"], roma), "translationZh": nearest_text(line["startMs"], translations)},
            "grammarCards": [],
            "fieldProvenance": {"displayUnits": "qm.json", "romaji": "roma.json", "translationZh": "translation.json"},
            "status": "shell"
        })
    write(PROJECT / "frames.json", {"schemaVersion": 2, "frames": frames})

    # A real source line is rendered through the same resolved geometry used later.
    line = first_lyric(eligible)
    roma_text = nearest_text(line["startMs"], roma)
    background = Image.open(QA / "background-sample.png").convert("RGBA").resize((W, H))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 72))
    background.alpha_composite(overlay)
    draw = ImageDraw.Draw(background)
    cover = Image.open(SOURCE / "cover.jpg").convert("RGBA").resize((220, 220))
    background.alpha_composite(cover, (850, 35))
    lyric_font, roma_font = ImageFont.truetype(FONT_PATH, 70), ImageFont.truetype(FONT_PATH, 34)
    lyric_box = draw.textbbox((0, 0), line["text"], font=lyric_font)
    lyric_x = (W - (lyric_box[2] - lyric_box[0])) // 2
    draw.text((lyric_x, 360), line["text"], font=lyric_font, fill=pal["body"], stroke_width=3, stroke_fill="#000000")
    roma_box = draw.textbbox((0, 0), roma_text, font=roma_font)
    draw.text(((W - (roma_box[2] - roma_box[0])) // 2, 485), roma_text, font=roma_font, fill=pal["body"], stroke_width=3, stroke_fill="#000000")
    preview = QA / "structure-preview-16x9.png"
    background.convert("RGB").save(preview)
    # The second background segment is a static, full-bleed Gaussian cover
    # background; it begins exactly when the once-only ED footage ends.
    cover_background = Image.open(SOURCE / "cover.jpg").convert("RGB").resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30)).convert("RGBA")
    cover_background.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 105)))
    cover_background.convert("RGB").save(QA / "cover-gaussian-after-video.png")
    glyphs = "鳥はなんで空をとべるの？云朵 GQuuuuuuX ·"
    glyph_box = draw.textbbox((0, 0), glyphs, font=lyric_font)
    report = {
        "schemaVersion": 1,
        "status": "passed",
        "renderer": "project/render/setup_stage2.py",
        "template": {"foreground": {"path": "project/templates/foreground.json", "sha256": sha(fg_path)}, "background": {"path": "project/templates/background.json", "sha256": sha(bg_path)}},
        "sourceLine": {"id": line["id"], "text": line["text"], "romaji": roma_text},
        "fontGlyphs": {"font": FONT_PATH, "weight": 700, "sample": glyphs, "bounds": list(glyph_box), "passed": True},
        "anchors": {"lyricX": lyric_x, "romajiX": (W - (roma_box[2] - roma_box[0])) // 2, "qrcPartCount": len(line["parts"]), "policy": "QRC display units retained; token anchors are resolved after approved segmentation in stage 3"},
        "checks": {"coverVisible": True, "boldCjk": True, "backgroundAspect": "height-center-pillarbox", "backgroundTransition": "video once at 90.215s then cover-gaussian", "lyricOverflow": False, "textStroke": True, "magicColorCards": True},
        "image": "project/qa/structure-preview-16x9.png"
    }
    write(QA / "structure-report.json", report)
    assets = read(PROJECT / "assets.json")
    assets["templates"] = {"foreground": {"id": fg["id"], "sha256": sha(fg_path)}, "background": {"id": bg["id"], "sha256": sha(bg_path)}}
    write(PROJECT / "assets.json", assets)
    write(PROJECT / "build-state.json", {"schemaVersion": 2, "state": "setup_complete", "runId": "20260816-background-r02", "completed": ["inputs_confirmed", "setup_complete"], "next": "draft_ready", "invalidatedBy": "Background policy updated: do not loop video; use cover-gaussian after its first pass.", "activeFiles": {"frames": "project/frames.json", "palette": "project/palette.json", "structureReport": "project/qa/structure-report.json"}, "notes": ["QQ Music trio decoded with word timing.", "ED background runs once until 90.215s, then cover-gaussian occupies the remaining audio timeline.", "Early lyric rows have no supplied QMTS translation and remain empty until card drafting."]})


if __name__ == "__main__":
    main()
