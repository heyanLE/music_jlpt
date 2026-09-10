"""Apply the accepted translation role's grammar-aligned card meanings."""
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
    proposal_path = PROJECT / "proposals" / "translation-aligned.json"
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
    if proposal.get("baseFrameSha256") != before_sha:
        raise SystemExit("Aligned translation proposal is stale")
    frames = json.loads(frames_path.read_text(encoding="utf-8"))
    by_id = {frame["id"]: frame for frame in frames["frames"]}
    for change in proposal["changes"]:
        frame = by_id[change["frameId"]]
        if change["field"] == "caption.translationZh":
            frame["caption"]["translationZh"] = change["new"]
        elif change["field"] == "grammarCards":
            cards = [card for card in change["new"] if card.get("token")]
            for card in cards:
                # User-approved visual convention: card row 3 is short POS.
                card["grammarStructureZh"] = card.get("posZh", card.get("grammarStructureZh", ""))
                card["status"] = "human-confirmed"
                card["reviewRequired"] = False
            frame["grammarCards"] = cards
        frame["status"] = "human-confirmed"
    frames_path.write_text(json.dumps(frames, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    after_sha = sha(frames_path)
    log_path = PROJECT / "review" / "merge-log.json"
    log = json.loads(log_path.read_text(encoding="utf-8"))
    log["framesAfterSha256"] = after_sha
    log.setdefault("mergedProposalFiles", []).append("project/proposals/translation-aligned.json")
    log["cardCount"] = sum(len(frame["grammarCards"]) for frame in frames["frames"])
    log["alignmentCorrection"] = "Accepted translation proposal was remapped to grammar phrase boundaries; one empty duplicate l043 terminal-particle card removed."
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"before": before_sha, "after": after_sha, "cards": log["cardCount"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
