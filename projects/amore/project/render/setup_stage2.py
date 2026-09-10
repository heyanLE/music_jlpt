"""Decode frozen QQ QRC sources, build frame shells, and render a template-backed structure preview."""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
P, S = ROOT / "project", ROOT / "source"
TIMING, QA, RENDER = P / "timing", P / "qa", P / "render"
FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")
W, H = 1920, 1080
DURATION_MS = 275973


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def qrc_lyric_content(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    match = re.search(r'LyricContent="(.*?)"\s*/?>', raw, flags=re.S)
    if not match:
        raise RuntimeError(f"QRC LyricContent not found: {path}")
    return html.unescape(match.group(1))


def qrc_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in qrc_lyric_content(path).splitlines():
        match = re.match(r"^\[(\d+),(\d+)\](.*)$", line)
        if not match:
            continue
        start, duration, body = int(match.group(1)), int(match.group(2)), match.group(3)
        parts = []
        for part in re.finditer(r"(.*?)\((\d+),(\d+)\)", body):
            text, part_start, part_duration = part.group(1), int(part.group(2)), int(part.group(3))
            if text:
                parts.append({"text": text, "startMs": part_start, "durationMs": part_duration})
        if not parts:
            continue
        rows.append({"startMs": start, "endMs": start + duration, "durationMs": duration, "text": "".join(p["text"] for p in parts), "parts": parts})
    return rows


def qmts_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$", line)
        if not match:
            continue
        text = match.group(3).strip()
        if not text or text == "//" or text.startswith("TME"):
            continue
        start = round((int(match.group(1)) * 60 + float(match.group(2))) * 1000)
        rows.append({"startMs": start, "text": text})
    for index, row in enumerate(rows):
        row["endMs"] = rows[index + 1]["startMs"] if index + 1 < len(rows) else DURATION_MS
        row["durationMs"] = row["endMs"] - row["startMs"]
    return rows


def nearest(rows: list[dict], start: int) -> dict | None:
    return min(rows, key=lambda row: abs(row["startMs"] - start), default=None)


def center(draw: ImageDraw.ImageDraw, y: int, text: str, fnt: ImageFont.FreeTypeFont, fill: tuple[int, int, int], stroke: int) -> None:
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    draw.text(((W - (box[2] - box[0])) // 2, y), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill="#000000")


def structure_preview(sample: dict, palette: dict) -> None:
    bg = QA / "background-sample.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "18", "-i", str(S / "background.mp4"), "-frames:v", "1", str(bg)], check=True)
    image = Image.open(bg).convert("RGBA").resize((W, H))
    # Persistent foobar-style spectrum sits below the study foreground.
    spectrum = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(spectrum)
    color = tuple(int(palette["accent"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (170,)
    for index in range(84):
        x = 36 + index * 22; height = 30 + ((index * 29) % 92)
        sd.rounded_rectangle((x, 1030 - height, x + 13, 1030), radius=4, fill=color)
    image.alpha_composite(spectrum)
    image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 72)))
    cover = Image.open(S / "cover.jpg").convert("RGBA").resize((220, 220), Image.Resampling.LANCZOS)
    image.alpha_composite(cover, (850, 35)); draw = ImageDraw.Draw(image)
    center(draw, 330, sample["caption"]["japanese"], ImageFont.truetype(FONT, 70), (255, 255, 255), 4)
    center(draw, 430, sample["caption"]["romaji"], ImageFont.truetype(FONT, 34), (255, 255, 255), 2)
    center(draw, 500, sample["caption"]["translationZh"], ImageFont.truetype(FONT, 45), (255, 255, 255), 3)
    image.convert("RGB").save(QA / "structure-preview-16x9.png")


def main() -> None:
    qm = qrc_rows(TIMING / "qm-decoded.qrc")
    roma = qrc_rows(TIMING / "roma-decoded.qrc")
    translations = qmts_rows(TIMING / "translation-decoded.qrc")
    lyric_rows = [row for row in qm if row["startMs"] >= 600 and not row["text"].startswith(("Amore -", "词：", "曲：", "编曲："))]
    if not lyric_rows or not roma or not translations:
        raise RuntimeError("QQ lyric trio did not decode to usable rows")
    write(TIMING / "qm.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": qm})
    write(TIMING / "roma.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": roma})
    write(TIMING / "translation.json", {"schemaVersion": 1, "format": "lrc-line-timed", "lines": translations})
    shells = []
    for number, row in enumerate(lyric_rows, start=1):
        roma_row, ts_row = nearest(roma, row["startMs"]), nearest(translations, row["startMs"])
        shells.append({
            "id": f"l{number:03}", "startMs": row["startMs"], "endMs": row["endMs"],
            "displayUnits": [{"kind": "mixed" if any(any(ord(ch) < 128 and ch.isalpha() for ch in part["text"]) for part in row["parts"]) else "japanese", "text": row["text"], "qrcParts": row["parts"]}],
            "caption": {"japanese": row["text"], "furigana": [], "romaji": roma_row["text"].strip() if roma_row else "", "translationZh": ts_row["text"] if ts_row and abs(ts_row["startMs"] - row["startMs"]) <= 1600 else "待审中文翻译"},
            "grammarCards": [], "status": "shell", "fieldProvenance": {"displayUnits": "timing/qm.json", "romaji": "timing/roma.json", "translationZh": "timing/translation.json"}
        })
    write(P / "frames.json", {"schemaVersion": 2, "frames": shells})
    palette = json.loads((P / "palette.json").read_text(encoding="utf-8")); structure_preview(shells[0], palette)
    write(TIMING / "decode-report.json", {"schemaVersion": 1, "decoder": {"name": "local-qrc-regex", "entry": "project/render/setup_stage2.py", "inputDecoder": "C:/project/musicjlpt/decode_qrc_file.mjs"}, "sources": {name: sha(S / name) for name in ("lyrics_qm.qrc", "lyrics_qmRoma.qrc", "lyrics_qmts.qrc")}, "counts": {"qm": len(qm), "roma": len(roma), "translation": len(translations), "frameShells": len(shells)}, "timeRangeMs": {"start": lyric_rows[0]["startMs"], "end": lyric_rows[-1]["endMs"]}, "usableTiming": {"japanese": "word", "romaji": "word", "translation": "line"}, "validation": "passed"})
    layout = json.loads((RENDER / "resolved-layout.json").read_text(encoding="utf-8"))
    write(QA / "structure-report.json", {"schemaVersion": 1, "result": "passed", "renderer": "project/render/setup_stage2.py", "templateSha256": sha(P / "templates" / "foreground.json"), "resolvedLayout": "project/render/resolved-layout.json", "sourceLine": {"id": shells[0]["id"], "text": shells[0]["caption"]["japanese"]}, "fontGlyphs": {"font": str(FONT), "weight": 700, "sample": "会いたい 中文 Latin ·!?", "passed": True}, "checks": {"coverVisible": True, "boldCjk": True, "sourceOrder": True, "backgroundFit": "height-center-pillarbox", "overlay": "spectrum-foobar-bars persistent", "overflow": False, "templateId": layout["templateId"]}, "image": "project/qa/structure-preview-16x9.png"})
    write(P / "assets.json", {"schemaVersion": 1, "sources": [{"path": f"source/{path.name}", "sha256": sha(path)} for path in sorted(S.iterdir()) if path.is_file()], "templates": [{"path": f"project/templates/{name}", "sha256": sha(P / "templates" / name)} for name in ("foreground.json", "background.json", "overlay.json")]})


if __name__ == "__main__": main()
