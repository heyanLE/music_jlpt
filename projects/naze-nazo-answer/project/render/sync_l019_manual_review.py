"""Sync the user's l019 Markdown correction into frames.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
TIMING = PROJECT / "timing" / "qm.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    timing = load(TIMING)
    timing_row = next(row for row in timing["lines"] if row.get("startMs") == 92928)
    timing_row["text"] = "秘密の鍵はこじ開けない 寄り添うだけで ごめん"
    timing_row["parts"] = [part for part in timing_row["parts"] if part["text"] not in {"く", "(", "＿", ")"}]
    dump(TIMING, timing)

    frames = load(FRAMES)
    frame = next(row for row in frames["frames"] if row["id"] == "l019")
    new_text = "秘密の鍵はこじ開けない 寄り添うだけで ごめん"
    frame["caption"]["japanese"] = new_text
    unit = frame["displayUnits"][0]
    unit["text"] = new_text
    # The manual review removes an erroneous trailing QRC fragment: く(＿).
    unit["qrcParts"] = [part for part in unit["qrcParts"] if part["text"] not in {"く", "(", "＿", ")"}]
    frame["status"] = "human-corrected"
    frame.setdefault("fieldProvenance", {})["japanese"] = "user-edited current review Markdown: l019"
    dump(FRAMES, frames)

    audit = {
        "schemaVersion": 1,
        "userWording": "l019 我有修改，重新生成",
        "frame": "l019",
        "change": "Removed trailing erroneous QRC fragment く(＿) from displayed lyric while retaining reviewed Chinese and cards.",
        "framesSha256": sha(FRAMES),
        "timingSha256": sha(TIMING),
    }
    dump(PROJECT / "review" / "l019-manual-sync.json", audit)
    merge = load(PROJECT / "review" / "merge-log.json")
    merge["framesAfterSha256"] = audit["framesSha256"]
    merge["l019ManualCorrection"] = audit["change"]
    dump(PROJECT / "review" / "merge-log.json", merge)
    decision = load(PROJECT / "review" / "review-decision.json")
    decision["frameSha256"] = audit["framesSha256"]
    decision["mergeLogSha256"] = sha(PROJECT / "review" / "merge-log.json")
    decision["renderAuthorized"] = False
    decision["l019ManualCorrection"] = "accepted"
    dump(PROJECT / "review" / "review-decision.json", decision)
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    main()
