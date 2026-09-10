from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
USER_WORDING = "采纳全部提案"
PART_RE = re.compile(r"^([^\[\]]+)(?:\[(\d+)\])?$")


def load(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM is forbidden: {path}")
    return json.loads(raw.decode("utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_parent(frame: dict, field: str):
    parts = field.split(".")
    current = frame
    for raw in parts[:-1]:
        match = PART_RE.fullmatch(raw)
        if not match:
            raise ValueError(f"Unsupported field path: {field}")
        key, index = match.group(1), match.group(2)
        current = current[key]
        if index is not None:
            current = current[int(index)]
    final = PART_RE.fullmatch(parts[-1])
    if not final:
        raise ValueError(f"Unsupported field path: {field}")
    return current, final.group(1), final.group(2)


def get_value(frame: dict, field: str):
    parent, key, index = resolve_parent(frame, field)
    value = parent[key]
    return value[int(index)] if index is not None else value


def set_value(frame: dict, field: str, value) -> None:
    parent, key, index = resolve_parent(frame, field)
    if index is None:
        parent[key] = copy.deepcopy(value)
    else:
        parent[key][int(index)] = copy.deepcopy(value)


def card_meaning(card: dict) -> str:
    return card.get("functionZh") or card.get("zhMeaning") or ""


def review_markdown(frames: list[dict]) -> str:
    lines = [
        "# 星降る海 · 已确认词卡",
        "",
        "> 已按用户决定“采纳全部提案”合并多角色联网复审结果。",
        "",
    ]
    for frame in frames:
        caption = frame["caption"]
        lines.extend(
            [
                f"## {frame['id']} · {frame['startMs'] / 1000:.3f}s",
                "",
                f"日文：{caption.get('japanese', '')}",
                "",
                f"中文：{caption.get('translationZh', '')}",
                "",
                f"罗马音：{caption.get('romaji', '')}",
                "",
                "词卡：",
                "",
            ]
        )
        for card in frame.get("grammarCards", []):
            source = f"｜外来词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(
                f"- `{card['token']}`｜{card.get('reading', '')}｜{card.get('romaji', '')}｜{card_meaning(card)}｜{card.get('grammarStructureZh', '')}{source}"
            )
        if not frame.get("grammarCards"):
            lines.append("- 无学习词卡")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    project_dir = PROJECT / "project"
    frames_path = project_dir / "frames.json"
    integration_path = project_dir / "review" / "integration-report.json"
    audit_path = project_dir / "review" / "assisted-review-audit.json"
    document = load(frames_path)
    integration = load(integration_path)
    audit = load(audit_path)
    before_sha = sha(frames_path)

    if audit.get("baseFrameSha256") != before_sha:
        raise SystemExit("Assisted-review audit is stale for the current frames")
    if integration.get("baseFrameSha256") != before_sha:
        raise SystemExit("Integration report is stale for the current frames")
    if audit.get("integration", {}).get("sha256") != sha(integration_path):
        raise SystemExit("Integration report hash does not match sealed audit")

    backup = project_dir / "review" / f"frames-before-approved-{before_sha[:12]}.json"
    if not backup.exists():
        shutil.copy2(frames_path, backup)

    frame_map = {frame["id"]: frame for frame in document["frames"]}
    applied = []
    for change in integration["recommendedChanges"]:
        frame = frame_map[change["frameId"]]
        actual = get_value(frame, change["field"])
        if actual != change["old"]:
            raise SystemExit(
                f"Old value mismatch at {change['frameId']} {change['field']}: proposal is not safely applicable"
            )
        set_value(frame, change["field"], change["new"])
        applied.append({"frameId": change["frameId"], "field": change["field"]})

    for frame in document["frames"]:
        frame["analysisStatus"] = "assisted-review-approved"
        frame["status"] = "human-confirmed"
        frame["reviewRequired"] = False
        frame.setdefault("fieldProvenance", {})["approval"] = USER_WORDING
        for card in frame.get("grammarCards", []):
            card["status"] = "human-confirmed"
            card["reviewRequired"] = False
            card.setdefault("fieldProvenance", {})["approval"] = USER_WORDING

    document["reviewStatus"] = "approved"
    document["reviewUserWording"] = USER_WORDING
    write(frames_path, document)
    after_sha = sha(frames_path)

    review_path = PROJECT / "deliverables" / "review" / "hoshi-furu-umi-review.md"
    review_path.write_text(review_markdown(document["frames"]), encoding="utf-8", newline="\n")

    audit_sha = sha(audit_path)
    merge_log_path = project_dir / "review" / "merge-log.json"
    merge_log = {
        "schemaVersion": 2,
        "status": "completed",
        "scope": "all",
        "userWording": USER_WORDING,
        "mergedAt": datetime.now(timezone.utc).isoformat(),
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "appliedIntegratedChanges": len(applied),
        "sourceProposalFiles": audit["proposalFiles"],
        "integrationReport": {
            "file": "project/review/integration-report.json",
            "sha256": sha(integration_path),
        },
        "assistedReviewAudit": {
            "file": "project/review/assisted-review-audit.json",
            "sha256": audit_sha,
        },
        "renderAuthorized": False,
    }
    write(merge_log_path, merge_log)

    decision = {
        "schemaVersion": 2,
        "content": "approved",
        "scope": "all",
        "renderAuthorized": False,
        "userWording": USER_WORDING,
        "frameSha256": after_sha,
        "assistedReviewAuditSha256": audit_sha,
        "mergeLogSha256": sha(merge_log_path),
    }
    write(project_dir / "review" / "content-decision.json", decision)

    state_path = project_dir / "build-state.json"
    state = load(state_path)
    state["stage"] = "review_approved"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append(
        f"User approved all {len(applied)} integrated assisted-review changes verbatim: {USER_WORDING}"
    )
    write(state_path, state)

    print(
        json.dumps(
            {
                "framesBeforeSha256": before_sha,
                "framesAfterSha256": after_sha,
                "appliedIntegratedChanges": len(applied),
                "mergeLogSha256": sha(merge_log_path),
                "contentDecision": str(project_dir / "review" / "content-decision.json"),
                "reviewDocument": str(review_path),
                "renderAuthorized": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
