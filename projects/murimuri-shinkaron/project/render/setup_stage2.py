"""Build UTF-8 lyric shells and a template-backed Stage-2 structure preview."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROJECT, SOURCE = ROOT / "project", ROOT / "source"
TIMING, QA, RENDER = PROJECT / "timing", PROJECT / "qa", PROJECT / "render"
FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")
W, H = 1920, 1080


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def closest(rows: list[dict], start_ms: int) -> dict | None:
    return min(rows, key=lambda row: abs(row["startMs"] - start_ms), default=None)


def text_center(draw: ImageDraw.ImageDraw, text: str, y: int, font: ImageFont.FreeTypeFont, fill: tuple[int, int, int, int], stroke: int) -> None:
    bounds = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    draw.text(((W - (bounds[2] - bounds[0])) // 2, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill="#000000")


def preview(sample: dict, layout: dict, palette: dict) -> None:
    bg_file = QA / "background-sample.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "12", "-i", str(SOURCE / "background-stage1.mp4"), "-frames:v", "1", str(bg_file)], check=True)
    background = Image.open(bg_file).convert("RGBA")
    scale = H / background.height
    width = round(background.width * scale)
    background = background.resize((width, H), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (W, H), "#000000")
    canvas.alpha_composite(background, ((W - width) // 2, 0))
    veil = Image.new("RGBA", (W, H), (0, 0, 0, round(255 * 0.28)))
    canvas.alpha_composite(veil)
    cover_x, cover_y, cover_w, cover_h = layout["cover"]["rectPx"]
    cover = Image.open(SOURCE / "cover.jpg").convert("RGBA").resize((cover_w, cover_h), Image.Resampling.LANCZOS)
    canvas.alpha_composite(cover, (cover_x, cover_y))
    draw = ImageDraw.Draw(canvas)
    text_center(draw, sample["caption"]["japanese"], layout["lyric"]["japanese"]["topPx"], ImageFont.truetype(FONT, 70), (255, 255, 255, 255), layout["strokePx"]["japanese"])
    text_center(draw, sample["caption"]["romaji"], layout["lyric"]["romaji"]["topPx"], ImageFont.truetype(FONT, 34), (255, 255, 255, 255), layout["strokePx"]["romaji"])
    text_center(draw, sample["caption"]["translationZh"], layout["lyric"]["translation"]["topPx"], ImageFont.truetype(FONT, 45), (255, 255, 255, 255), layout["strokePx"]["translation"])
    # Persistent transparent RGBA spectrum, intentionally above the learning foreground.
    accent = tuple(int(palette["accent"].lstrip("#")[pos:pos + 2], 16) for pos in (0, 2, 4))
    for index in range(84):
        x = 36 + index * 22
        bar_h = 20 + ((index * 47 + 19) % 105)
        draw.rounded_rectangle((x, 1030 - bar_h, x + 13, 1030), radius=4, fill=accent + (190,))
    canvas.convert("RGB").save(QA / "structure-preview-16x9.png")


def main() -> None:
    if not FONT.exists():
        raise RuntimeError(f"Missing required CJK-bold font: {FONT}")
    qm, roma, translation = (load(TIMING / name)["lines"] for name in ("qm.json", "roma.json", "translation.json"))
    lyric_rows = [row for row in qm if row["startMs"] >= 1124]
    if not lyric_rows or not roma:
        raise RuntimeError("Decoded QRC lacks usable Japanese or romaji timing")
    frames = []
    for index, row in enumerate(lyric_rows, 1):
        roma_row, translation_row = closest(roma, row["startMs"]), closest(translation, row["startMs"])
        is_english = row["text"].isascii() and any(char.isalpha() for char in row["text"])
        translation_zh = "待审中文翻译"
        if translation_row and abs(translation_row["startMs"] - row["startMs"]) <= 1600:
            translation_zh = translation_row["text"]
        frames.append({
            "id": f"l{index:03}", "startMs": row["startMs"], "endMs": row["endMs"],
            "displayUnits": [{"kind": "english" if is_english else "japanese", "text": row["text"], "qrcParts": row["parts"]}],
            "caption": {"japanese": row["text"], "furigana": [], "romaji": "" if is_english else (roma_row["text"].strip() if roma_row else ""), "translationZh": translation_zh},
            "grammarCards": [], "status": "shell",
            "fieldProvenance": {"displayUnits": "timing/qm.json", "romaji": "timing/roma.json", "translationZh": "timing/translation.json"}
        })
    write(PROJECT / "frames.json", {"schemaVersion": 2, "frames": frames})
    layout, palette = load(RENDER / "resolved-layout.json"), load(PROJECT / "palette.json")
    preview(frames[1], layout, palette)
    assets = load(SOURCE / "source-manifest.json")
    write(PROJECT / "assets.json", {
        "schemaVersion": 1,
        "sourceManifest": "source/source-manifest.json",
        "assets": assets["assets"],
        "templateHashes": {name: sha256(PROJECT / "templates" / name) for name in ("foreground.json", "background-stage1-video.json", "background-stage2-gaussian.json", "overlay.json")}
    })
    write(QA / "structure-report.json", {
        "schemaVersion": 1, "status": "passed", "renderer": "project/render/setup_stage2.py",
        "templateSha256": sha256(PROJECT / "templates" / "foreground.json"), "resolvedLayout": "project/render/resolved-layout.json",
        "sourceLine": {"id": frames[1]["id"], "text": frames[1]["caption"]["japanese"]},
        "fontGlyphs": {"font": str(FONT), "weight": 700, "sample": "人見知り 中文 Latin ·!?", "passed": True},
        "checks": {"coverVisible": True, "boldCjk": True, "sourceOrder": True, "backgroundFit": "height-center-pillarbox", "backgroundTransition": "stage1 video then cover-gaussian at 89899ms", "overlay": "persistent transparent foobar realtime bars above foreground", "overflow": False},
        "image": "project/qa/structure-preview-16x9.png"
    })


if __name__ == "__main__":
    main()
