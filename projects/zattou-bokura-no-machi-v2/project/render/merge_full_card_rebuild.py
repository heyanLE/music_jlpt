"""Apply the user-approved v2 full-card proposal without altering timing data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES_PATH = PROJECT / "frames.json"
PROPOSED_PATH = PROJECT / "review" / "full-card-proposed-frames.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    before_sha = sha(FRAMES_PATH)
    source = json.loads(FRAMES_PATH.read_text(encoding="utf-8"))
    proposed = json.loads(PROPOSED_PATH.read_text(encoding="utf-8"))
    if proposed.get("baseFrameSha256") != before_sha:
        raise SystemExit("The integrated review is stale for current project/frames.json")

    proposed_by_id = {frame["id"]: frame for frame in proposed["frames"]}
    frame_ids = {frame["id"] for frame in source["frames"]}
    if frame_ids != set(proposed_by_id):
        raise SystemExit("Integrated proposal frame set does not match project/frames.json")

    applied = []
    for frame in source["frames"]:
        candidate = proposed_by_id[frame["id"]]
        caption = candidate["caption"].copy()
        caption["furigana"] = candidate.get("furigana", [])
        frame["caption"] = caption
        frame["grammarCards"] = candidate.get("grammarCards", [])
        frame["status"] = "human-confirmed"
        frame["fieldProvenance"] = {
            "caption": "lexical/translation multi-role review + user accepted",
            "grammarCards": "lexical/grammar/translation multi-role review + user accepted",
        }
        applied.append({"frameId": frame["id"], "fields": ["caption", "grammarCards"]})

    FRAMES_PATH.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    after_sha = sha(FRAMES_PATH)
    log = {
        "schemaVersion": 2,
        "userWording": "采纳全部提案",
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "mergedProposalFiles": [
            "project/proposals/lexical-v2.json",
            "project/proposals/grammar-v2.json",
            "project/proposals/translation-v2.json",
            "project/review/full-card-proposed-frames.json",
        ],
        "appliedFrames": applied,
        "cardCount": sum(len(frame["grammarCards"]) for frame in source["frames"]),
        "metadataPolicy": "QRC metadata rows l001-l005 excluded before this merge",
    }
    (PROJECT / "review" / "merge-log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"frames": len(source["frames"]), "cards": log["cardCount"], "framesAfterSha256": after_sha}, ensure_ascii=False))


if __name__ == "__main__":
    main()
