#!/usr/bin/env python3
"""Record the user's content decision and the merge binding the render gate requires.

Any flow that installs reviewed content must end with the two files the gate reads:
`project/review/merge-log.json` (binding the frames before and after the accepted
merge) and `project/review/review-decision.json` (the user's verbatim wording, bound
to the audit and the merge log). This script writes exactly those two, refuses
ambiguous or placeholder wording, and never touches frames.json.

Usage
    python record_content_decision.py PROJECT_ROOT --user-wording "VERBATIM"
        [--scope TEXT] [--frames-before SHA] [--source FILE ...] [--apply-review FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

AMBIGUOUS_WORDINGS = {"继续", "开始", "可以", "下一步", "继续吧", "ok", "okay"}
PLACEHOLDER_MARKERS = ("REHEARSAL", "TEST-ONLY", "PLACEHOLDER", "DRYRUN", "DRY-RUN", "SANDBOX")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--user-wording", required=True)
    parser.add_argument("--scope", default="all reviewed content")
    parser.add_argument("--frames-before", help="Hash of the frames the accepted merge started from")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--apply-review", type=Path,
                        help="Merge log written when the reviewed cards were installed; used for the before-hash and the summary")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    frames = project / "frames.json"
    audit = project / "review" / "assisted-review-audit.json"
    if not frames.is_file():
        raise SystemExit("project/frames.json is missing")
    if not audit.is_file():
        raise SystemExit("Seal the review before recording a decision (assisted-review-audit.json is missing)")

    wording = args.user_wording.strip()
    if not wording:
        raise SystemExit("--user-wording must not be empty")
    if wording in AMBIGUOUS_WORDINGS:
        raise SystemExit(f"Ambiguous wording is not a content decision: {wording!r}")
    if any(marker in wording.upper() for marker in PLACEHOLDER_MARKERS):
        raise SystemExit(f"Placeholder wording is not a content decision: {wording!r}")

    frames_after = sha(frames)
    summary: dict = {}
    sealed_base = load(audit).get("baseFrameSha256")
    frames_before = args.frames_before
    if args.apply_review:
        applied = load(args.apply_review.resolve())
        summary = {"units": applied.get("units"), "cards": applied.get("cards"),
                   "perFrame": applied.get("perFrame")}
    # The accepted merge is "the reviewed draft became this content". Intermediate
    # steps (re-applying the review, user corrections, chunk merging) have their own
    # logs, so the binding that matters - and the one the render gate re-derives - is
    # the sealed draft; using a later intermediate would break the ancestor chain.
    frames_before = frames_before or sealed_base
    if not frames_before:
        raise SystemExit("Provide --frames-before, or seal an audit that records the draft hash")
    if frames_before == frames_after:
        raise SystemExit("frames.json is unchanged; nothing to record as a merge")

    merge_log = {
        "schemaVersion": 2,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
        "framesBeforeSha256": frames_before,
        "framesAfterSha256": frames_after,
        "scope": args.scope,
        "appliedReview": summary or None,
        "sourceProposals": [{"file": value, "sha256": sha(Path(value) if Path(value).is_absolute() else root / value)}
                            for value in args.source],
        "confirmedFrames": "all",
    }
    write(project / "review" / "merge-log.json", merge_log)

    decision = {
        "schemaVersion": 2,
        "content": "approved",
        "scope": args.scope,
        "renderAuthorized": False,
        "userWording": wording,
        "wordingIsVerbatim": True,
        "frameSha256": frames_after,
        "assistedReviewAuditSha256": sha(audit),
        "mergeLogSha256": sha(project / "review" / "merge-log.json"),
    }
    write(project / "review" / "review-decision.json", decision)
    print(json.dumps({
        "mergeLog": "project/review/merge-log.json",
        "reviewDecision": "project/review/review-decision.json",
        "framesBeforeSha256": frames_before,
        "framesAfterSha256": frames_after,
        "userWording": wording,
        "note": "renderAuthorized stays false; authorize_render.py binds the render separately",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
