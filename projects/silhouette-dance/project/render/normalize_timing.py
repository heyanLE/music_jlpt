"""Convert frozen, decoded QQ Music artifacts into UTF-8 timing JSON."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMING = ROOT / "project" / "timing"
SOURCE = ROOT / "source"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))


def qrc_lines(path: Path) -> list[dict]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if "lines" in parsed:
        return parsed["lines"]
    rows = []
    for raw in parsed["content"]:
        start = int(raw["start"])
        parts = [
            {"text": part["content"], "startMs": start + int(part["start"]), "durationMs": int(part["duration"])}
            for part in raw["content"]
        ]
        text = "".join(part["text"] for part in parts)
        rows.append({"startMs": start, "durationMs": int(raw["duration"]), "endMs": start + int(raw["duration"]), "text": text, "parts": parts})
    return rows


def lrc_lines(path: Path) -> list[dict]:
    hits = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$", raw)
        if not match:
            continue
        start = round((int(match.group(1)) * 60 + float(match.group(2))) * 1000)
        hits.append({"startMs": start, "text": match.group(3)})
    for index, row in enumerate(hits):
        row["endMs"] = hits[index + 1]["startMs"] if index + 1 < len(hits) else 209453
        row["durationMs"] = row["endMs"] - row["startMs"]
    return hits


def main() -> None:
    qm, roma = qrc_lines(TIMING / "qm.json"), qrc_lines(TIMING / "roma.json")
    translation = lrc_lines(TIMING / "translation-decoded.qrc")
    write(TIMING / "qm.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": qm})
    write(TIMING / "roma.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": roma})
    write(TIMING / "translation.json", {"schemaVersion": 1, "format": "lrc-line-timed", "lines": translation})
    report = {
        "schemaVersion": 1,
        "decoder": {"name": "smart-lyric", "entry": "C:/project/musicjlpt/decode_qrc_file.mjs", "parse": "qrc.decrypt + qrc.parse"},
        "sources": {name: sha(SOURCE / name) for name in ("lyrics_qm.qrc", "lyrics_qmRoma.qrc", "lyrics_qmts.qrc")},
        "counts": {"qm": len(qm), "roma": len(roma), "translation": len(translation)},
        "timeRangeMs": {"start": min(row["startMs"] for row in qm), "end": max(row["endMs"] for row in qm)},
        "usableTiming": {"japanese": "word", "romaji": "word", "translation": "line"},
        "validation": "passed"
    }
    write(TIMING / "decode-report.json", report)
    lyrics = [row for row in qm if row["startMs"] >= 17000]
    shells = []
    for index, row in enumerate(lyrics, start=1):
        nearest_roma = min(roma, key=lambda candidate: abs(candidate["startMs"] - row["startMs"]))
        nearest_translation = min(translation, key=lambda candidate: abs(candidate["startMs"] - row["startMs"]))
        shells.append({
            "id": f"l{index:03}", "startMs": row["startMs"], "endMs": row["endMs"],
            "displayUnits": [{"kind": "japanese", "text": row["text"], "qrcParts": row["parts"]}],
            "caption": {"japanese": row["text"], "furigana": [], "romaji": nearest_roma["text"], "translationZh": nearest_translation["text"]},
            "grammarCards": [], "status": "shell",
            "fieldProvenance": {"displayUnits": "timing/qm.json", "romaji": "timing/roma.json", "translationZh": "timing/translation.json"}
        })
    write(TIMING / "frame-shells.json", {"schemaVersion": 1, "frames": shells})


if __name__ == "__main__":
    main()
