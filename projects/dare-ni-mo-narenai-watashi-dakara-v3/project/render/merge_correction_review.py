from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES_PATH = PROJECT / "frames.json"
INTEGRATION_PATH = PROJECT / "review" / "correction-integration-report.json"
AUDIT_PATH = PROJECT / "review" / "assisted-review-audit.json"
USER_WORDING = "采纳全部提案  "


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    json.loads(path.read_text(encoding="utf-8"))


def path_parts(field: str) -> list[str | int]:
    parts: list[str | int] = []
    for name, index in re.findall(r"([^.[\]]+)|\[(\d+)\]", field):
        parts.append(int(index) if index else name)
    return parts


def get_value(root: object, field: str) -> object:
    current = root
    for part in path_parts(field):
        if isinstance(part, int):
            current = current[part]  # type: ignore[index]
        else:
            if not isinstance(current, dict):
                raise TypeError(f"cannot read {field}: {part} is not inside an object")
            current = current.get(part)
    return current


def set_value(root: object, field: str, value: object) -> None:
    parts = path_parts(field)
    current = root
    for part in parts[:-1]:
        if isinstance(part, int):
            current = current[part]  # type: ignore[index]
        else:
            current = current[part]  # type: ignore[index]
    last = parts[-1]
    if isinstance(last, int):
        current[last] = copy.deepcopy(value)  # type: ignore[index]
    elif value is None:
        current.pop(last, None)  # type: ignore[union-attr]
    else:
        current[last] = copy.deepcopy(value)  # type: ignore[index]


def selector_key(frame_id: str, field: str) -> str:
    return f"{frame_id}:{field}"


def main() -> None:
    before_sha = sha256(FRAMES_PATH)
    frames_payload = load(FRAMES_PATH)
    integration = load(INTEGRATION_PATH)
    if integration["baseFrameSha256"] != before_sha:
        raise SystemExit("correction integration is stale for current frames")
    frames = {frame["id"]: frame for frame in frames_payload["frames"]}
    proposal_paths = {
        "lexical": PROJECT / "proposals" / "correction-lexical.json",
        "grammar": PROJECT / "proposals" / "correction-grammar.json",
        "translation": PROJECT / "proposals" / "correction-translation.json",
    }
    selectors = {
        item["sourceProposalFile"]: set(item.get("excludedFields", []))
        for item in integration["recommendedProposalSet"]["selectors"]
    }
    changed_frames: set[str] = set()
    applied: list[dict] = []

    for role in ("lexical", "grammar", "translation"):
        proposal_path = proposal_paths[role]
        proposal = load(proposal_path)
        if proposal["baseFrameSha256"] != before_sha:
            raise SystemExit(f"stale {role} correction proposal")
        rel = proposal_path.relative_to(ROOT).as_posix()
        excluded = selectors[rel]
        for change in proposal["changes"]:
            key = selector_key(change["frameId"], change["field"])
            if key in excluded:
                continue
            frame = frames[change["frameId"]]
            current = get_value(frame, change["field"])
            if current != change["old"]:
                raise SystemExit(f"old value mismatch for {role} {key}")
            set_value(frame, change["field"], change["new"])
            changed_frames.add(change["frameId"])
            applied.append({"source": rel, "frameId": change["frameId"], "field": change["field"]})

    for change in integration["recommendedProposalSet"]["resolvedChanges"]:
        frame = frames[change["frameId"]]
        set_value(frame, change["field"], change["new"])
        changed_frames.add(change["frameId"])
        applied.append({"source": "integration", "id": change["id"], "frameId": change["frameId"], "field": change["field"]})

    for change in integration["recommendedProposalSet"]["integrationAddedRecommendations"]:
        frame = frames[change["frameId"]]
        for field in change["fields"]:
            current = get_value(frame, field)
            if current != change["old"]:
                raise SystemExit(f"integration-added old value mismatch for {change['frameId']}:{field}")
            set_value(frame, field, change["new"])
            changed_frames.add(change["frameId"])
            applied.append({"source": "integration-added", "frameId": change["frameId"], "field": field})

    for frame_id in changed_frames:
        frame = frames[frame_id]
        frame["status"] = "human-confirmed"
        provenance = frame.setdefault("fieldProvenance", {})
        provenance["correctionReview"] = "three-role correction review + integration audit + user accepted"
        for card in frame.get("grammarCards", []):
            card["status"] = "human-confirmed"

    write(FRAMES_PATH, frames_payload)
    after_sha = sha256(FRAMES_PATH)
    merge_log = {
        "schemaVersion": 2,
        "userWording": USER_WORDING,
        "scope": "all recommended correction proposals",
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "assistedReviewAuditSha256": sha256(AUDIT_PATH),
        "mergedProposalFiles": [path.relative_to(ROOT).as_posix() for path in proposal_paths.values()],
        "integrationReport": INTEGRATION_PATH.relative_to(ROOT).as_posix(),
        "integrationReportSha256": sha256(INTEGRATION_PATH),
        "appliedFieldCount": len(applied),
        "changedFrameIds": sorted(changed_frames),
        "resolvedConflictIds": [item["id"] for item in integration["conflicts"]],
        "applied": applied,
    }
    write(PROJECT / "review" / "merge-log.json", merge_log)
    print(json.dumps({
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "changedFrames": len(changed_frames),
        "appliedFields": len(applied),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
