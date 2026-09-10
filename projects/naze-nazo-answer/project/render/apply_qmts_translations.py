"""Apply a user-supplied QQ Music translation track to reviewed frames.

This changes only caption.translationZh.  It deliberately preserves the
human-reviewed Japanese text, timings, readings and grammar cards.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
DECODED = PROJECT / "work" / "new-qmts-decoded.qrc"
SOURCE = ROOT / "source" / "lyrics_qmts.qrc"
OUT_TRANSLATIONS = PROJECT / "timing" / "translation.json"

STAMP = re.compile(r"^\[(\d+):(\d+\.\d+)\](.*)$")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qrc_translation_rows(text: str):
    rows = []
    for raw in text.splitlines():
        match = STAMP.match(raw)
        if not match:
            continue
        minute, second, value = match.groups()
        # QQ attribution and blank separator cues must never become captions.
        if not value or value == "//" or value.startswith("TME"):
            continue
        rows.append({"startMs": round((int(minute) * 60 + float(second)) * 1000), "text": value})
    rows.sort(key=lambda row: row["startMs"])
    for index, row in enumerate(rows):
        row["endMs"] = rows[index + 1]["startMs"] if index + 1 < len(rows) else 240_413
        row["durationMs"] = row["endMs"] - row["startMs"]
    return rows


def main() -> None:
    if not DECODED.exists():
        raise RuntimeError(f"Missing decoded user translation: {DECODED}")
    frames = load(FRAMES)
    translations = qrc_translation_rows(DECODED.read_text(encoding="utf-8"))
    changed = []
    for index, frame in enumerate(frames["frames"]):
        start, end = frame["startMs"], frame["endMs"]
        # The two QRC editions differ by a few dozen milliseconds at a line
        # boundary.  Attribution must be based on the *start* of a translated
        # line, rather than interval overlap (which would pull the prior line
        # into the next current frame).  The vocal opens after the first
        # translation cue, so the first frame also accepts that one lead-in.
        lower = 0 if index == 0 else start - 150
        # The final sung "因为……" cue begins 462 ms before the last QRC
        # display unit, so retain it with the closing line rather than lose it.
        if index == len(frames["frames"]) - 1:
            lower = start - 500
        matches = [row["text"] for row in translations if lower <= row["startMs"] < end]
        if not matches:
            continue
        value = " ".join(matches)
        caption = frame["caption"]
        if caption.get("translationZh") != value:
            changed.append({"id": frame["id"], "old": caption.get("translationZh", ""), "new": value})
            caption["translationZh"] = value
            frame["status"] = "human-corrected"
            frame.setdefault("fieldProvenance", {})["translationZh"] = "user-supplied QQ Music QMTS track"

    # Freeze the exact provided source and derived timing alongside the project.
    SOURCE.write_bytes(Path(r"C:\Users\eke_l\AppData\Roaming\Tencent\QQMusic\QQMusicCache\QQMusicLyricNew\増井優花_名探偵プリキュア！_熊田茜音 (くまだあかね) - なぜ？謎？！ANSWER (WHY_MYSTERY_!ANSWER) (WHY_MYSTERY_!ANSWER) - 240 - 『名探偵プリキュア！』主題歌シングル【通常盤】_qmts.qrc").read_bytes())
    dump(OUT_TRANSLATIONS, {"schemaVersion": 1, "format": "qrc-line-timed", "lines": translations})
    dump(FRAMES, frames)

    audit = {
        "schemaVersion": 1,
        "userWording": "中文改为这里歌词的中文",
        "source": str(SOURCE),
        "translationRows": len(translations),
        "changedFrames": changed,
        "framesSha256": sha(FRAMES),
        "sourceSha256": sha(SOURCE),
    }
    dump(PROJECT / "review" / "qmts-translation-override.json", audit)
    merge = load(PROJECT / "review" / "merge-log.json")
    merge["framesAfterSha256"] = audit["framesSha256"]
    merge["translationOverride"] = "All line translations replaced by the user-supplied QQ Music QMTS track."
    dump(PROJECT / "review" / "merge-log.json", merge)
    decision = load(PROJECT / "review" / "review-decision.json")
    decision["frameSha256"] = audit["framesSha256"]
    decision["mergeLogSha256"] = sha(PROJECT / "review" / "merge-log.json")
    decision["translationOverride"] = "User-supplied QQ Music QMTS translations applied; render authorization invalidated."
    decision["renderAuthorized"] = False
    dump(PROJECT / "review" / "review-decision.json", decision)
    print(json.dumps({"changedFrames": len(changed), "framesSha256": audit["framesSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
