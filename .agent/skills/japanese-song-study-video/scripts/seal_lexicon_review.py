#!/usr/bin/env python3
"""Seal a lexicon-RAG draft plus its targeted online review.

This replaces the three-role (lexical/grammar/translation) audit for projects
drafted from the workspace lexicon. The review obligation is unchanged - an
explicit user content decision and a separate render authorization are still
required - but only the spans the lexicon could not vouch for are reviewed, and
they are reviewed once, online, instead of three times in parallel.

Usage
    python seal_lexicon_review.py PROJECT_ROOT --online-review FILE [--queue FILE] [--lexicon FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

MODE = "lexicon-rag-targeted-online"
ONLINE_ROLES = ("online", "lexicon-online")


def load(path: Path) -> dict:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM is forbidden: {path}")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Top level must be object: {path}")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root: Path, value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the project root: {path}") from exc
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--online-review", required=True)
    parser.add_argument("--queue", default="project/review/rag-review-queue.json")
    parser.add_argument("--lexicon", default="lexicon/lexicon.json")
    args = parser.parse_args()

    root = args.project_root.resolve()
    workspace = root.parents[1]
    project = root / "project"
    frames_path = project / "frames.json"
    if not frames_path.is_file():
        raise SystemExit("project/frames.json is missing")

    review_path = inside(root, args.online_review, "online review artifact")
    review = load(review_path)
    role = str(review.get("reviewRole", ""))
    if role not in ONLINE_ROLES:
        raise SystemExit(f"Online review must declare reviewRole one of {ONLINE_ROLES}, got {role!r}")
    if review.get("status") != "completed":
        raise SystemExit("Online review artifact must have status=completed")
    if not isinstance(review.get("changes", review.get("proposals")), list):
        raise SystemExit("Online review must contain a changes/proposals list")

    queue_path = inside(root, args.queue, "RAG review queue")
    queue = load(queue_path)
    lexicon_path = Path(args.lexicon)
    if not lexicon_path.is_absolute():
        lexicon_path = workspace / lexicon_path
    if not lexicon_path.is_file():
        raise SystemExit(f"Lexicon is missing: {lexicon_path}")

    lexicon_document = load(lexicon_path)
    # generatedAt changes on every rebuild, so compare the content revision.
    lexicon_sha = str(lexicon_document.get("contentSha256") or sha(lexicon_path))
    if queue.get("lexiconSha256") != lexicon_sha:
        raise SystemExit("Review queue is stale for the current lexicon; re-run draft_cards_from_lexicon.py")
    declared = review.get("lexiconSha256")
    if declared and declared != lexicon_sha:
        raise SystemExit("Online review was produced against a different lexicon revision")
    if review.get("queueSha256") and review["queueSha256"] != sha(queue_path):
        raise SystemExit("Online review was produced against a different review queue")

    # Refuse to seal a review that does not actually answer the queue. The render gate
    # re-checks this from disk; failing here is simply earlier and clearer.
    expected = {
        f"{entry['frameId']}::{unit['text']}"
        for entry in queue.get("queue", [])
        for unit in entry.get("units", [])
    }
    changes = review.get("changes", review.get("proposals", []))
    answered = []
    for change in changes:
        if not isinstance(change, dict):
            raise SystemExit("Online review changes must be objects")
        frame_id, unit_text = str(change.get("frameId", "")), str(change.get("unit", change.get("text", "")))
        if not frame_id or not unit_text:
            raise SystemExit(f"Online review change must name frameId and unit: {change!r}")
        if not str(change.get("resolution", change.get("new", ""))).strip():
            raise SystemExit(f"Online review change must carry a resolution: {frame_id}::{unit_text}")
        answered.append(f"{frame_id}::{unit_text}")
    missing = sorted(expected - set(answered))
    if missing:
        raise SystemExit(f"Online review left {len(missing)} queued unit(s) unanswered, e.g. {missing[:3]}")
    unknown = sorted(set(answered) - expected)
    if unknown:
        raise SystemExit(f"Online review answered units that were never queued: {unknown[:3]}")
    if len(answered) != len(set(answered)):
        raise SystemExit("Online review answered the same unit more than once")

    frames_document = load(frames_path)
    frames = frames_document.get("frames", [])
    card_count = sum(len(frame.get("grammarCards", [])) for frame in frames)
    totals = queue.get("totals", {})
    if totals.get("frames") not in (None, len(frames)):
        raise SystemExit("Review queue frame count disagrees with frames.json")
    if totals.get("reviewUnits") not in (None, len(expected)):
        raise SystemExit("Review queue totals.reviewUnits disagrees with its own queue")
    if card_count == 0 and not review.get("allRowsEnglish"):
        raise SystemExit("A draft with no cards needs an explicit allRowsEnglish declaration in the online review")

    audit = {
        "schemaVersion": 2,
        "mode": MODE,
        "status": "completed",
        "sealedAt": datetime.now(timezone.utc).isoformat(),
        "baseFrameSha256": sha(frames_path),
        "roles": ["online"],
        "lexicon": {"path": str(lexicon_path.relative_to(workspace)).replace("\\", "/") if lexicon_path.is_relative_to(workspace) else str(lexicon_path),
                    "sha256": lexicon_sha},
        "ragQueue": {"file": queue_path.relative_to(root).as_posix(), "sha256": sha(queue_path), "totals": totals},
        "onlineReview": {"file": review_path.relative_to(root).as_posix(), "sha256": sha(review_path), "changes": len(changes)},
        "coverage": {**totals, "checkedUnits": len(answered)},
        "content": {"frames": len(frames), "cards": card_count, "allRowsEnglish": bool(review.get("allRowsEnglish")),
                    "draftedCards": totals.get("cardsDrafted"), "lowConfidenceCards": totals.get("lowConfidenceProposed")},
        "next": "explicit-user-content-decision",
    }
    output = project / "review" / "assisted-review-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    load(output)
    print(json.dumps({"output": str(output.relative_to(root)).replace("\\", "/"), "mode": MODE, "coverage": audit["coverage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
