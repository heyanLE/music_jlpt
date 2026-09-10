from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_path(obj: dict, path: str):
    value = obj
    for key in path.split("."):
        value = value[key]
    return value


def set_path(obj: dict, path: str, value) -> None:
    parts = path.split(".")
    target = obj
    for key in parts[:-1]:
        target = target[key]
    target[parts[-1]] = value


def main() -> None:
    frames_path = PROJECT / "frames.json"
    before_sha = sha(frames_path)
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    by_id = {frame["id"]: frame for frame in data["frames"]}
    applied = []
    for role in ("lexical", "grammar", "translation"):
        proposal = json.loads((PROJECT / "proposals" / f"{role}.json").read_text(encoding="utf-8"))
        if proposal.get("baseFrameSha256") != before_sha:
            raise SystemExit(f"stale proposal: {role}")
        for change in proposal.get("changes", []):
            frame = by_id[change["frameId"]]
            current = get_path(frame, change["field"])
            if current != change.get("old"):
                raise SystemExit(f"old value mismatch: {change['frameId']} {change['field']}")
            set_path(frame, change["field"], copy.deepcopy(change["new"]))
            frame.setdefault("fieldProvenance", {})[change["field"]] = f"{role}-review + user-accepted"
            applied.append({"role": role, "frameId": change["frameId"], "field": change["field"], "confidence": change.get("confidence")})
    for frame in data["frames"]:
        frame["status"] = "human-confirmed"
    frames_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    after_sha = sha(frames_path)
    log = {
        "schemaVersion": 2,
        "userWording": "采纳全部提案",
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "mergedProposalFiles": ["project/proposals/lexical.json", "project/proposals/grammar.json", "project/proposals/translation.json"],
        "appliedChanges": applied,
        "metadataPolicy": "QRC metadata frames l001-l005 excluded before this merge",
    }
    (PROJECT / "review" / "merge-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(data["frames"]), "appliedChanges": len(applied), "framesAfterSha256": after_sha}, ensure_ascii=False))


if __name__ == "__main__":
    main()
