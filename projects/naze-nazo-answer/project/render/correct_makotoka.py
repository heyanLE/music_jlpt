"""Apply the user's confirmed correction for the two corrupted QRC lyric rows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
TIMING = PROJECT / "timing" / "qm.json"
OLD = "うそかまごこと"
NEW = "うそかまことか"


def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def dump(path: Path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()


def correct_parts(parts: list[dict], extended: bool) -> list[dict]:
    start = next(i for i, item in enumerate(parts) if item["text"] == "ま")
    # l011: map ま ご こ と -> ま こ と か.  l032 has an extra final か;
    # collapse the corrupted ご+こ timings into the intended こ timing.
    if not extended:
        for index, value in enumerate(("ま", "こ", "と", "か")):
            parts[start + index]["text"] = value
        return parts
    ma, bad_go, bad_ko, to, ka = parts[start:start + 5]
    fixed = [ma, {**bad_go, "text": "こ", "endMs": bad_ko["endMs"], "durationMs": bad_ko["endMs"] - bad_go["startMs"]}, {**to, "text": "と"}, {**ka, "text": "か"}]
    return parts[:start] + fixed + parts[start + 5:]


def correct_cards(cards: list[dict], extended: bool) -> list[dict]:
    index = next(i for i, card in enumerate(cards) if card["token"] == "まごこと")
    truth = dict(cards[index])
    truth.update({"token": "まこと", "reading": "まこと", "romaji": "makoto", "grammarStructureZh": "名词", "posZh": "名词", "zhMeaning": "真相；真话", "status": "human-confirmed"})
    truth.pop("functionZh", None)
    truth.setdefault("fieldProvenance", {})["token"] = "user correction: まことか"
    truth["fieldProvenance"]["reading"] = "user correction: まことか"
    truth["fieldProvenance"]["romaji"] = "user correction: まことか"
    choice = {"token": "か", "reading": "か", "romaji": "ka", "grammarStructureZh": "助词", "posZh": "助词", "functionZh": "表示选择", "render": True, "showJlpt": False, "status": "human-confirmed", "fieldProvenance": {"token": "user correction: まことか", "meaningOrFunction": "user correction: まことか", "grammarStructureZh": "user correction: まことか"}}
    if extended:
        cards[index] = truth
        return cards
    return cards[:index] + [truth, choice] + cards[index + 1:]


def main() -> None:
    timing = load(TIMING)
    timing_changes = 0
    for row in timing["lines"]:
        if row["text"].startswith(OLD):
            extended = row["text"].startswith(OLD + "か")
            row["text"] = row["text"].replace(OLD + "か" if extended else OLD, NEW, 1)
            row["parts"] = correct_parts(row["parts"], extended)
            timing_changes += 1
    if timing_changes != 2: raise RuntimeError(f"Expected 2 timing rows, found {timing_changes}")
    dump(TIMING, timing)

    frames = load(FRAMES)
    corrected = []
    for frame in frames["frames"]:
        text = frame["caption"]["japanese"]
        if not text.startswith(OLD): continue
        extended = text.startswith(OLD + "か")
        frame["caption"]["japanese"] = text.replace(OLD + "か" if extended else OLD, NEW, 1)
        frame["caption"]["translationZh"] = "分辨谎言还是真相，找到带来笑容的答案。"
        for unit in frame["displayUnits"]:
            unit["text"] = unit["text"].replace(OLD + "か" if extended else OLD, NEW, 1)
            unit["qrcParts"] = correct_parts(unit["qrcParts"], extended)
        frame["grammarCards"] = correct_cards(frame["grammarCards"], extended)
        frame["caption"]["romaji"] = " ".join(card["romaji"] for card in frame["grammarCards"])
        frame["status"] = "human-corrected"
        frame.setdefault("fieldProvenance", {})["japanese"] = "user correction: まことか"
        corrected.append(frame["id"])
    if corrected != ["l011", "l032"]: raise RuntimeError(f"Expected l011/l032, got {corrected}")
    dump(FRAMES, frames)

    correction = {"schemaVersion": 1, "userWording": "うそかまごこと見極めて 应该是　うそかまことか見極めて，修改歌词和词卡", "frames": corrected, "changes": ["caption/display units/QRC timing", "まごこと -> まこと", "inserted/corrected choice particle か", "romaji and Chinese translation"], "framesSha256": sha(FRAMES), "timingSha256": sha(TIMING)}
    dump(PROJECT / "review" / "makotoka-correction.json", correction)
    merge = load(PROJECT / "review" / "merge-log.json")
    merge["framesAfterSha256"] = correction["framesSha256"]
    merge["userCorrection"] = "l011/l032 corrected from まごこと to まことか by user instruction"
    dump(PROJECT / "review" / "merge-log.json", merge)
    decision = load(PROJECT / "review" / "review-decision.json")
    decision["frameSha256"] = correction["framesSha256"]
    decision["mergeLogSha256"] = sha(PROJECT / "review" / "merge-log.json")
    decision["userCorrection"] = "l011/l032 まことか correction accepted"
    dump(PROJECT / "review" / "review-decision.json", decision)
    print(json.dumps({"corrected": corrected, "framesSha256": correction["framesSha256"], "timingSha256": correction["timingSha256"]}, ensure_ascii=False))


if __name__ == "__main__": main()
