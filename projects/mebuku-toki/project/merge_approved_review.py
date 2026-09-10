#!/usr/bin/env python3
"""Merge the user-approved integrated proposal and record immutable evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
INTEGRATION = PROJECT / "review" / "integration-report.json"
AUDIT = PROJECT / "review" / "assisted-review-audit.json"
MERGE_LOG = PROJECT / "review" / "merge-log.json"
DECISION = PROJECT / "review" / "content-decision.json"
REVIEW = ROOT / "deliverables" / "review" / "mebuku-toki-review-approved.md"
USER_WORDING = "采纳全部提案"


def load(path: Path) -> dict:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM forbidden: {path}")
    return json.loads(raw.decode("utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    load(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frames_doc = load(FRAMES)
    integration = load(INTEGRATION)
    audit = load(AUDIT)
    before_sha = sha(FRAMES)
    if integration.get("baseFrameSha256") != before_sha or audit.get("baseFrameSha256") != before_sha:
        raise SystemExit("Approved review artifacts are stale for current frames.json")
    if audit.get("integration", {}).get("sha256") != sha(INTEGRATION):
        raise SystemExit("Integration report changed after assisted-review sealing")

    frames = {frame["id"]: frame for frame in frames_doc["frames"]}
    changes = integration["recommendedProposalSet"]["changes"]
    for change in changes:
        frame = frames[change["frameId"]]
        field = change["field"]
        if field == "grammarCards":
            if frame["grammarCards"] != change["old"]:
                raise SystemExit(f"Old-value mismatch: {change['frameId']} {field}")
            frame["grammarCards"] = copy.deepcopy(change["new"])
        elif field.startswith("caption."):
            key = field.split(".", 1)[1]
            if frame["caption"].get(key) != change["old"]:
                raise SystemExit(f"Old-value mismatch: {change['frameId']} {field}")
            frame["caption"][key] = copy.deepcopy(change["new"])
        else:
            raise SystemExit(f"Unsupported integrated field: {field}")
        frame["status"] = "reviewed-user-approved"

    write(FRAMES, frames_doc)
    after_sha = sha(FRAMES)
    if after_sha == before_sha:
        raise SystemExit("Approved merge produced no frame change")

    proposal_files = []
    for role in ("lexical", "grammar", "translation"):
        path = PROJECT / "proposals" / f"{role}.json"
        proposal_files.append({"role": role, "file": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
    merge_log = {
        "schemaVersion": 2,
        "status": "completed",
        "scope": "all",
        "userWording": USER_WORDING,
        "mergedAt": datetime.now(timezone.utc).isoformat(),
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "appliedIntegratedChanges": len(changes),
        "sourceProposalFiles": proposal_files,
        "integrationReport": {"file": INTEGRATION.relative_to(ROOT).as_posix(), "sha256": sha(INTEGRATION)},
        "assistedReviewAudit": {"file": AUDIT.relative_to(ROOT).as_posix(), "sha256": sha(AUDIT)},
        "renderAuthorized": False,
    }
    write(MERGE_LOG, merge_log)
    decision = {
        "schemaVersion": 2,
        "content": "approved",
        "scope": "all",
        "renderAuthorized": False,
        "userWording": USER_WORDING,
        "frameSha256": after_sha,
        "assistedReviewAuditSha256": sha(AUDIT),
        "mergeLogSha256": sha(MERGE_LOG),
    }
    write(DECISION, decision)

    state_path = PROJECT / "build-state.json"
    state = load(state_path)
    state["stage"] = "review_approved"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append(f"User approved all integrated proposals verbatim: {USER_WORDING}")
    write(state_path, state)

    lines = [
        "# 芽吹くとき｜已批准词卡",
        "",
        f"用户决定：{USER_WORDING}。内容哈希：`{after_sha}`。本批准不包含视频渲染授权。",
        "",
    ]
    for frame in frames_doc["frames"]:
        caption = frame["caption"]
        lines.extend([
            f"## {frame['id']}　{frame['startMs'] / 1000:06.2f}",
            f"歌词：{caption['japanese']}",
            f"中文：{caption['translationZh']}",
            "",
            "词卡：",
        ])
        for card in frame["grammarCards"]:
            semantic = card.get("functionZh") or card.get("zhMeaning")
            source = f"｜词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}｜{semantic}｜{card['grammarStructureZh']}{source}")
        lines.append("")
    REVIEW.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"framesBeforeSha256": before_sha, "framesAfterSha256": after_sha, "changes": len(changes), "decision": str(DECISION), "review": str(REVIEW)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
