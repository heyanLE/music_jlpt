"""Merge the user-approved full assisted-review scope into the sole frames source."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "project"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frames_path = P / "frames.json"; frame_doc = load(frames_path)
    changes, sources = {}, []
    for path in sorted((P / "proposals").glob("assisted-review-*.json")):
        doc = load(path); sources.append(str(path.relative_to(ROOT)))
        for proposal in doc.get("proposals", doc.get("items", [])):
            if proposal["frameId"] in changes:
                raise RuntimeError(f"Duplicate proposal: {proposal['frameId']}")
            changes[proposal["frameId"]] = proposal
    if set(changes) != {frame["id"] for frame in frame_doc["frames"]}:
        raise RuntimeError("The approved scope must cover every frame exactly once")
    log = []
    for frame in frame_doc["frames"]:
        proposal = changes[frame["id"]]
        before = {"translationZh": frame["caption"].get("translationZh"), "cards": frame.get("grammarCards", [])}
        frame["caption"]["translationZh"] = proposal.get("newTranslationZh", frame["caption"]["translationZh"])
        frame["caption"]["translationStatus"] = "human-approved-assisted-review"
        frame["grammarCards"] = [{**card, "status": "human-confirmed", "fieldProvenance": "user-approved assisted review 20260822"} for card in proposal.get("suggestedCards", [])]
        frame["status"] = "human-confirmed"
        frame.setdefault("fieldProvenance", {}).update({"caption.translationZh": "user-approved assisted review 20260822", "grammarCards": "user-approved assisted review 20260822"})
        log.append({"frameId": frame["id"], "translationChanged": before["translationZh"] != frame["caption"]["translationZh"], "cardCountBefore": len(before["cards"]), "cardCountAfter": len(frame["grammarCards"]), "tokenStructureChanged": bool(proposal.get("changesTokenStructure")), "proposalConfidence": proposal.get("confidence"), "evidence": proposal.get("evidence", [])})
    write(frames_path, frame_doc)
    write(P / "review" / "merge-log.json", {"schemaVersion": 1, "decision": "整体采纳", "sources": sources, "mergedFrames": len(log), "changes": log, "framesSha256": digest(frames_path)})
    write(P / "review" / "review-decision.json", {"schemaVersion": 1, "content": "approved", "scope": "all", "renderAuthorized": False, "userWording": "整体采纳", "frameSha256": digest(frames_path)})


if __name__ == "__main__": main()
