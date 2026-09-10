from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
INTEGRATION = PROJECT / "review" / "integration-report.json"
AUDIT = PROJECT / "review" / "assisted-review-audit.json"
USER_WORDING = "采纳全部提案"


def load(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"BOM forbidden: {path}")
    return json.loads(raw.decode("utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    load(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_path(frame: dict, field: str):
    parts = re.findall(r"[^.\[\]]+|\d+", field)
    target = frame
    for part in parts:
        target = target[int(part)] if isinstance(target, list) else target[part]
    return target


def set_path(frame: dict, field: str, value) -> None:
    parts = re.findall(r"[^.\[\]]+|\d+", field)
    target = frame
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list):
        target[int(last)] = copy.deepcopy(value)
    else:
        target[last] = copy.deepcopy(value)


def main() -> None:
    before_hash = sha(FRAMES)
    integration = load(INTEGRATION)
    audit = load(AUDIT)
    if integration.get("baseFrameSha256") != before_hash:
        raise SystemExit("Integration report is stale for current frames.json")
    if audit.get("baseFrameSha256") != before_hash:
        raise SystemExit("Assisted-review audit is stale for current frames.json")
    sealed_integration = audit.get("integration", {})
    if sealed_integration.get("sha256") != sha(INTEGRATION):
        raise SystemExit("Integration report no longer matches sealed audit")

    document = load(FRAMES)
    frames = {frame["id"]: frame for frame in document["frames"]}
    changes = integration["recommendedProposalSet"]["changes"]
    for index, change in enumerate(changes):
        frame = frames[change["frameId"]]
        current = get_path(frame, change["field"])
        if current != change["old"]:
            raise SystemExit(f"Old value mismatch at change {index}: {change['frameId']} {change['field']}")
        set_path(frame, change["field"], change["new"])

    for frame in document["frames"]:
        frame["status"] = "reviewed-user-approved"
        frame["analysisStatus"] = "user-approved-assisted-review"
        frame["reviewRequired"] = False
        for card in frame.get("grammarCards", []):
            card["status"] = "reviewed-user-approved"
            card["reviewRequired"] = False
            card.setdefault("fieldProvenance", {})["approval"] = "user adopted sealed assisted-review proposals"

    write(FRAMES, document)
    after_hash = sha(FRAMES)
    merge_log = {
        "schemaVersion": 2,
        "mergedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "all",
        "userWording": USER_WORDING,
        "framesBeforeSha256": before_hash,
        "framesAfterSha256": after_hash,
        "mergedProposalFiles": audit["proposalFiles"],
        "integration": audit["integration"],
        "mergedChangeCount": len(changes),
    }
    merge_path = PROJECT / "review" / "merge-log.json"
    write(merge_path, merge_log)
    decision = {
        "schemaVersion": 2,
        "content": "approved",
        "scope": "all",
        "renderAuthorized": False,
        "userWording": USER_WORDING,
        "frameSha256": after_hash,
        "assistedReviewAuditSha256": sha(AUDIT),
        "mergeLogSha256": sha(merge_path),
    }
    write(PROJECT / "review" / "content-decision.json", decision)
    print(json.dumps({"changes": len(changes), "before": before_hash, "after": after_hash}, ensure_ascii=False))


if __name__ == "__main__":
    main()
