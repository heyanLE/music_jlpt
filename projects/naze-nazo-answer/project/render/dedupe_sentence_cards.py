"""Remove exact duplicate grammar cards within an individual lyric frame."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(card: dict) -> tuple:
    return (
        card.get("token", ""), card.get("reading", ""), card.get("romaji", ""),
        card.get("zhMeaning", ""), card.get("functionZh", ""),
        card.get("grammarStructureZh", card.get("posZh", "")),
    )


def main() -> None:
    frames = load(FRAMES)
    report = []
    for frame in frames["frames"]:
        kept, seen, removed = [], set(), []
        for card in frame.get("grammarCards", []):
            key = signature(card)
            if key in seen:
                removed.append(card["token"])
            else:
                kept.append(card); seen.add(key)
        if removed:
            frame["grammarCards"] = kept
            frame["status"] = "human-corrected"
            report.append({"id": frame["id"], "removedExactDuplicates": removed})
    dump(FRAMES, frames)
    audit = {
        "schemaVersion": 1,
        "userWording": "同一局里一样的词卡只出现一次",
        "dedupeRule": "same token, reading, romaji, meaning/function and grammar structure within one frame",
        "affectedFrames": report,
        "framesSha256": sha(FRAMES),
    }
    dump(PROJECT / "review" / "sentence-card-deduplication.json", audit)
    merge = load(PROJECT / "review" / "merge-log.json")
    merge["framesAfterSha256"] = audit["framesSha256"]
    merge["sentenceCardDeduplication"] = audit["dedupeRule"]
    dump(PROJECT / "review" / "merge-log.json", merge)
    decision = load(PROJECT / "review" / "review-decision.json")
    decision["frameSha256"] = audit["framesSha256"]
    decision["mergeLogSha256"] = sha(PROJECT / "review" / "merge-log.json")
    decision["renderAuthorized"] = False
    dump(PROJECT / "review" / "review-decision.json", decision)
    print(json.dumps({"affectedFrames": len(report), "removedCards": sum(len(x["removedExactDuplicates"]) for x in report), "framesSha256": audit["framesSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
