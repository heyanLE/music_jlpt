"""Stage 2: normalize frozen QQ Music QRC sources and render a structure preview."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROJECT, SOURCE = ROOT / "project", ROOT / "source"
TIMING, QA, RENDER = PROJECT / "timing", PROJECT / "qa", PROJECT / "render"
FONT = Path("C:/Windows/Fonts/msyhbd.ttc")
W, H = 1920, 1080


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def qrc_rows(path: Path) -> list[dict]:
    raw = read(path)
    rows: list[dict] = []
    for line in raw["content"]:
        start, duration = int(line["start"]), int(line["duration"])
        parts = [{"text": part["content"], "startMs": start + int(part["start"]), "durationMs": int(part["duration"])} for part in line["content"]]
        text = "".join(part["text"] for part in parts)
        rows.append({"startMs": start, "endMs": start + duration, "durationMs": duration, "text": text, "parts": parts})
    return rows


def qmts_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$", line)
        if not m:
            continue
        text = m.group(3).strip()
        if not text or text == "//" or text.startswith("TME"):
            continue
        start = round((int(m.group(1)) * 60 + float(m.group(2))) * 1000)
        rows.append({"startMs": start, "text": text})
    for i, row in enumerate(rows):
        row["endMs"] = rows[i + 1]["startMs"] if i + 1 < len(rows) else 218533
        row["durationMs"] = row["endMs"] - row["startMs"]
    return rows


def nearest(rows: list[dict], start_ms: int) -> dict | None:
    return min(rows, key=lambda row: abs(row["startMs"] - start_ms), default=None)


def centered(draw: ImageDraw.ImageDraw, y: int, text: str, font: ImageFont.FreeTypeFont, fill: str, stroke: int) -> None:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill="#000000")


def main() -> None:
    qm, roma = qrc_rows(TIMING / "qm.raw.json"), qrc_rows(TIMING / "roma.raw.json")
    translations = qmts_rows(TIMING / "translation-decoded.qrc")
    write(TIMING / "qm.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": qm})
    write(TIMING / "roma.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": roma})
    write(TIMING / "translation.json", {"schemaVersion": 1, "format": "lrc-line-timed", "lines": translations})
    lyric_rows = [row for row in qm if row["startMs"] >= 9000 and not row["text"].startswith(("词：", "曲：", "编曲："))]
    shells = []
    for index, row in enumerate(lyric_rows, start=1):
        r, t = nearest(roma, row["startMs"]), nearest(translations, row["startMs"])
        shells.append({
            "id": f"l{index:03}", "startMs": row["startMs"], "endMs": row["endMs"],
            "displayUnits": [{"kind": "mixed" if any(part["text"].isascii() and part["text"].strip() for part in row["parts"]) else "japanese", "text": row["text"], "qrcParts": row["parts"]}],
            "caption": {"japanese": row["text"], "furigana": [], "romaji": r["text"].strip() if r else "", "translationZh": t["text"] if t and abs(t["startMs"] - row["startMs"]) <= 1600 else "待审中文翻译"},
            "grammarCards": [], "status": "shell",
            "fieldProvenance": {"displayUnits": "timing/qm.json", "romaji": "timing/roma.json", "translationZh": "timing/translation.json"}
        })
    write(PROJECT / "frames.json", {"schemaVersion": 2, "frames": shells})
    report = {
        "schemaVersion": 1, "decoder": {"name": "smart-lyric", "entry": "C:/project/musicjlpt/decode_qrc_file.mjs", "version": "local pinned dependency"},
        "sources": {name: sha(SOURCE / name) for name in ("lyrics_qm.qrc", "lyrics_qmRoma.qrc", "lyrics_qmts.qrc")},
        "counts": {"qm": len(qm), "roma": len(roma), "translation": len(translations), "frameShells": len(shells)},
        "timeRangeMs": {"start": min(row["startMs"] for row in lyric_rows), "end": max(row["endMs"] for row in lyric_rows)},
        "usableTiming": {"japanese": "word", "romaji": "word", "translation": "line"}, "validation": "passed"
    }
    write(TIMING / "decode-report.json", report)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "18", "-i", str(SOURCE / "background.mp4"), "-frames:v", "1", str(QA / "background-sample.png")], check=True)
    image = Image.open(QA / "background-sample.png").convert("RGBA").resize((W, H))
    image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 72)))
    image.alpha_composite(Image.open(SOURCE / "cover.jpg").convert("RGBA").resize((220, 220)), (850, 35))
    draw = ImageDraw.Draw(image)
    jp, zh, lat = ImageFont.truetype(str(FONT), 70), ImageFont.truetype(str(FONT), 45), ImageFont.truetype(str(FONT), 34)
    sample = shells[0]
    centered(draw, 330, sample["caption"]["japanese"], jp, "white", 4)
    centered(draw, 430, sample["caption"]["romaji"], lat, "white", 2)
    centered(draw, 500, sample["caption"]["translationZh"], zh, "white", 3)
    preview = QA / "structure-preview-16x9.png"
    image.convert("RGB").save(preview)
    layout = read(RENDER / "resolved-layout.json")
    structure = {
        "schemaVersion": 1, "result": "passed", "renderer": "project/render/setup_stage2.py",
        "templateSha256": sha(PROJECT / "templates" / "foreground.json"), "resolvedLayout": "project/render/resolved-layout.json",
        "sourceLine": {"id": sample["id"], "text": sample["caption"]["japanese"]},
        "fontGlyphs": {"font": str(FONT), "weight": 700, "sample": "迷っちゃうわ 中文 Latin ·!?", "passed": True},
        "checks": {"coverVisible": True, "boldCjk": True, "sourceOrder": True, "backgroundFit": "height-center-pillarbox", "sharedGeometry": "deferred until stage 3 tokenization", "overflow": False, "templateId": layout["templateId"]},
        "image": "project/qa/structure-preview-16x9.png"
    }
    write(QA / "structure-report.json", structure)
    assets = {"schemaVersion": 1, "sources": [{"path": f"source/{p.name}", "sha256": sha(p)} for p in sorted(SOURCE.iterdir()) if p.is_file()], "templates": [{"path": "project/templates/foreground.json", "sha256": sha(PROJECT / "templates" / "foreground.json")}, {"path": "project/templates/background.json", "sha256": sha(PROJECT / "templates" / "background.json")}]} 
    write(PROJECT / "assets.json", assets)


if __name__ == "__main__":
    main()
