from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frames_path = PROJECT / "frames.json"
    before_sha = sha(frames_path)
    original = json.loads(frames_path.read_text(encoding="utf-8"))
    proposal = json.loads((PROJECT / "review" / "integrated-proposed-frames.json").read_text(encoding="utf-8"))
    if proposal.get("baseFrameSha256") != before_sha:
        raise SystemExit("Integrated review is stale for current frames")
    proposed = {frame["id"]: frame for frame in proposal["frames"]}
    if {frame["id"] for frame in original["frames"]} != set(proposed):
        raise SystemExit("Frame IDs differ between draft and integrated proposal")
    for frame in original["frames"]:
        revised = proposed[frame["id"]]
        frame["caption"] = revised["caption"]
        frame["grammarCards"] = revised["grammarCards"]
        frame["status"] = "human-confirmed"
        frame["fieldProvenance"] = {
            "caption": "lexical/translation assisted review + user accepted",
            "grammarCards": "lexical/grammar/translation assisted review + user accepted",
        }
    frames_path.write_text(json.dumps(original, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    after_sha = sha(frames_path)
    log = {
        "schemaVersion": 2,
        "userWording": "采纳全部提案",
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "mergedProposalFiles": [
            "project/proposals/lexical.json", "project/proposals/grammar.json", "project/proposals/translation.json",
            "project/review/integrated-proposed-frames.json",
        ],
        "frameCount": len(original["frames"]),
        "cardCount": sum(len(frame["grammarCards"]) for frame in original["frames"]),
    }
    (PROJECT / "review" / "merge-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"frames": log["frameCount"], "cards": log["cardCount"], "framesAfterSha256": after_sha}, ensure_ascii=False))


if __name__ == "__main__":
    main()
