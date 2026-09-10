"""Apply the user-confirmed やさしさならひびくかな correction."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"; FRAMES = PROJECT / "frames.json"; TIMING = PROJECT / "timing" / "qm.json"
OLD = "やさしさならびくかな"; NEW = "やさしさならひびくかな"
def load(path): return json.loads(path.read_text(encoding="utf-8"))
def dump(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def parts_fixed(parts):
    index = next(i for i, part in enumerate(parts) if part["text"] == "び")
    bad = parts[index]; midpoint = bad["startMs"] + (bad["endMs"] - bad["startMs"]) // 2
    hi = {**bad, "text": "ひ", "endMs": midpoint, "durationMs": midpoint - bad["startMs"]}
    bi = {**bad, "text": "び", "startMs": midpoint, "durationMs": bad["endMs"] - midpoint}
    return parts[:index] + [hi, bi] + parts[index + 1:]

def main():
    timing = load(TIMING); rows = [row for row in timing["lines"] if OLD in row["text"]]
    if len(rows) != 1: raise RuntimeError(f"Expected one timing row, got {len(rows)}")
    row = rows[0]; row["text"] = row["text"].replace(OLD, NEW, 1); row["parts"] = parts_fixed(row["parts"]); dump(TIMING, timing)
    frames = load(FRAMES); target = next(frame for frame in frames["frames"] if OLD in frame["caption"]["japanese"])
    target["caption"]["japanese"] = target["caption"]["japanese"].replace(OLD, NEW, 1)
    target["caption"]["translationZh"] = "若是温柔，是否会产生共鸣？想传递暖洋洋与怦然心动。"
    for unit in target["displayUnits"]:
        unit["text"] = unit["text"].replace(OLD, NEW, 1); unit["qrcParts"] = parts_fixed(unit["qrcParts"])
    card = next(card for card in target["grammarCards"] if card["token"] == "びくかな")
    card.update({"token": "ひびくかな", "reading": "ひびくかな", "romaji": "hibiku kana", "zhMeaning": "会有共鸣吗？", "grammarStructureZh": "疑问表达", "posZh": "疑问表达", "status": "human-confirmed"})
    card.setdefault("fieldProvenance", {})["token"] = "user correction: ひびくかな"; card["fieldProvenance"]["meaningOrFunction"] = "user correction: ひびくかな"
    target["caption"]["romaji"] = " ".join(card["romaji"] for card in target["grammarCards"]); target["status"] = "human-corrected"
    dump(FRAMES, frames)
    note = {"schemaVersion":1,"userWording":"やさしさならびくかな 应该是　やさしさならひびくかな","frames":[target["id"]],"framesSha256":sha(FRAMES),"timingSha256":sha(TIMING)}
    dump(PROJECT / "review" / "hibikukana-correction.json", note)
    merge = load(PROJECT / "review" / "merge-log.json"); merge["framesAfterSha256"] = note["framesSha256"]; merge["secondUserCorrection"] = "l028 corrected from びくかな to ひびくかな"; dump(PROJECT / "review" / "merge-log.json", merge)
    decision = load(PROJECT / "review" / "review-decision.json"); decision["frameSha256"] = note["framesSha256"]; decision["mergeLogSha256"] = sha(PROJECT / "review" / "merge-log.json"); decision["secondUserCorrection"] = "l028 ひびくかな correction accepted"; dump(PROJECT / "review" / "review-decision.json", decision)
    print(json.dumps({"frame":target["id"],"framesSha256":note["framesSha256"],"timingSha256":note["timingSha256"]},ensure_ascii=False))
if __name__ == "__main__": main()
