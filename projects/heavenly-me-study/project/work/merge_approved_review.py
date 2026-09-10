#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(r"C:\project\musicjlpt\projects\heavenly-me-study")
PROJECT = ROOT / "project"
FRAMES_PATH = PROJECT / "frames.json"
BASE_SHA = "a1e1a1247da27e4509dd9978abb2915128c7bd48bd42cef162ae539e50479499"
USER_WORDING = "整体采纳  "
PROPOSALS = {
    "lexical": PROJECT / "proposals" / "lexical.json",
    "grammar": PROJECT / "proposals" / "grammar.json",
    "translation": PROJECT / "proposals" / "translation.json",
}
AUDIT_PATH = PROJECT / "review" / "assisted-review-audit.json"
INTEGRATION_PATH = PROJECT / "review" / "integration-report.json"
MERGE_LOG_PATH = PROJECT / "review" / "merge-log.json"
DECISION_PATH = PROJECT / "review" / "review-decision.json"
REVIEW_MD_PATH = ROOT / "deliverables" / "review" / "heavenly-me-study-review.md"


def read_json(path: Path) -> dict:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"BOM is forbidden: {path}")
    return json.loads(raw.decode("utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parts(field: str) -> list[str]:
    return re.sub(r"\[(\d+)\]", r".\1", field).split(".")


def get_field(frame: dict, field: str):
    value = frame
    for key in parts(field):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def set_field(frame: dict, field: str, new_value) -> None:
    keys = parts(field)
    target = frame
    for key in keys[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    final = keys[-1]
    if isinstance(target, list):
        target[int(final)] = new_value
    else:
        target[final] = new_value


def card_meaning(card: dict) -> str:
    return card.get("zhMeaning") or card.get("functionZh") or ""


def render_review(frames: list[dict], frame_sha: str) -> str:
    lines = [
        "# Heavenly Me 词卡审核定稿",
        "",
        "状态：已通过多角色审核并由用户整体采纳；当前仍未授权渲染。",
        "",
        f"帧哈希：`{frame_sha}`",
        "",
    ]
    for frame in frames:
        caption = frame["caption"]
        lines.extend(
            [
                f"## {frame['id']}  `{frame['startMs']}–{frame['endMs']} ms`",
                "",
                f"日文：{caption['japanese']}",
                "",
                f"中文：{caption['translationZh']}",
                "",
                "确认词卡：",
                "",
            ]
        )
        for card in frame.get("grammarCards", []):
            lines.append(
                "- "
                + "｜".join(
                    [
                        card.get("token", ""),
                        card.get("reading", ""),
                        card.get("romaji", ""),
                        card_meaning(card),
                        card.get("grammarStructureZh", card.get("posZh", "")),
                    ]
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if DECISION_PATH.is_file() and read_json(DECISION_PATH).get("content") == "approved":
        print(json.dumps({"status": "already-approved", "frameSha256": sha256(FRAMES_PATH)}, ensure_ascii=False))
        return

    before_sha = sha256(FRAMES_PATH)
    if before_sha != BASE_SHA:
        raise RuntimeError(f"frames.json changed after review seal: {before_sha}")
    if not AUDIT_PATH.is_file() or not INTEGRATION_PATH.is_file():
        raise RuntimeError("sealed assisted review or integration report is missing")

    document = read_json(FRAMES_PATH)
    frames = document["frames"]
    by_id = {frame["id"]: frame for frame in frames}
    applied = []
    occupied: dict[tuple[str, str], object] = {}

    for role in ("lexical", "grammar", "translation"):
        proposal = read_json(PROPOSALS[role])
        if proposal.get("baseFrameSha256") != before_sha:
            raise RuntimeError(f"stale {role} proposal")
        for change in proposal["changes"]:
            frame_id = change["frameId"]
            field = change["field"]
            normalized = ".".join(parts(field))
            if role == "grammar" and frame_id in {"l018", "l040"} and normalized == "grammarCards.3.functionZh":
                continue
            key = (frame_id, normalized)
            if key in occupied and occupied[key] != change["new"]:
                raise RuntimeError(f"unresolved conflict: {frame_id} {field}")
            current = get_field(by_id[frame_id], field)
            if current != change["old"]:
                raise RuntimeError(f"old-value mismatch: {role} {frame_id} {field}")
            set_field(by_id[frame_id], field, change["new"])
            occupied[key] = change["new"]
            applied.append(
                {
                    "source": f"project/proposals/{role}.json",
                    "frameId": frame_id,
                    "field": field,
                }
            )

    if len(applied) != 140:
        raise RuntimeError(f"expected 140 applied proposal fields, got {len(applied)}")

    for frame in frames:
        frame["status"] = "human-confirmed"
        frame["caption"]["translationStatus"] = "human-confirmed-qmts-source"
        for card in frame.get("grammarCards", []):
            card["status"] = "human-confirmed"
            card["fieldProvenance"] = {
                "token": "human-confirmed after sealed lexical review",
                "reading": "human-confirmed after sealed lexical review",
                "romaji": "human-confirmed after sealed lexical review; pronunciation-based particles",
                "meaningOrFunction": "human-confirmed after sealed translation review",
                "grammarStructureZh": "human-confirmed after sealed grammar review",
            }

    write_json(FRAMES_PATH, document)
    after_sha = sha256(FRAMES_PATH)
    REVIEW_MD_PATH.write_text(render_review(frames, after_sha), encoding="utf-8", newline="\n")

    merge_log = {
        "schemaVersion": 2,
        "userWording": USER_WORDING,
        "scope": "all",
        "framesBeforeSha256": before_sha,
        "framesAfterSha256": after_sha,
        "assistedReviewAuditSha256": sha256(AUDIT_PATH),
        "mergedProposalFiles": [
            "project/proposals/lexical.json",
            "project/proposals/grammar.json",
            "project/proposals/translation.json",
        ],
        "integrationReport": "project/review/integration-report.json",
        "integrationReportSha256": sha256(INTEGRATION_PATH),
        "appliedFieldCount": len(applied),
        "changedFrameIds": sorted({item["frameId"] for item in applied}),
        "resolvedConflicts": [
            {
                "frameId": "l018",
                "field": "grammarCards[3].functionZh",
                "applied": "标示倒装后置的动作对象",
            },
            {
                "frameId": "l040",
                "field": "grammarCards[3].functionZh",
                "applied": "标示倒装后置的动作对象",
            },
        ],
        "applied": applied,
    }
    write_json(MERGE_LOG_PATH, merge_log)

    decision = {
        "schemaVersion": 2,
        "content": "approved",
        "scope": "all",
        "renderAuthorized": False,
        "userWording": USER_WORDING,
        "frameSha256": after_sha,
        "assistedReviewAuditSha256": sha256(AUDIT_PATH),
        "mergeLogSha256": sha256(MERGE_LOG_PATH),
    }
    write_json(DECISION_PATH, decision)

    state_path = PROJECT / "build-state.json"
    state = read_json(state_path)
    state["stage"] = "review_approved"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append(
        "2026-09-02: user accepted the complete sealed three-role review. "
        f"Applied {len(applied)} integrated field changes; frames SHA256 is {after_sha}. "
        "Rendering remains unauthorized until a separate explicit render instruction."
    )
    write_json(state_path, state)
    print(
        json.dumps(
            {
                "status": "approved",
                "appliedFieldCount": len(applied),
                "framesBeforeSha256": before_sha,
                "framesAfterSha256": after_sha,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
