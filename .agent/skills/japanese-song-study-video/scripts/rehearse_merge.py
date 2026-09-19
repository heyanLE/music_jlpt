#!/usr/bin/env python3
"""Rehearse the post-approval merge in a scratch copy before touching the project.

Answering "will the merge work?" after the user has already approved is too late.
This copies the JSON evidence into a scratch directory, runs apply_review_merge.py
and refresh_after_merge.py against the copy, asserts the generic invariants and
proves the real project files are byte-identical afterwards.

Usage
    python rehearse_merge.py PROJECT_ROOT [--accepted FILE] [--scratch DIR] [--keep]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
GUARDED = ("project/frames.json", "project/review/review-decision.json", "project/review/merge-log.json",
           "project/build-state.json", "project/particle-functions.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--accepted", type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    accepted_source = args.accepted or project / "review" / "accepted-changes.json"
    if not accepted_source.is_file():
        raise SystemExit(f"Accepted change set is missing: {accepted_source}")
    scratch = args.scratch or project / "work" / "merge-rehearsal" / root.name
    before = {name: sha(root / name) if (root / name).is_file() else None for name in GUARDED}

    # A change set can only be rehearsed while it still applies. After the merge has
    # been applied for real, the recorded base hash no longer matches and rehearsing
    # is meaningless - report that plainly instead of as a pipeline failure.
    accepted_document = load(accepted_source)
    current_frames_sha = before["project/frames.json"]
    if accepted_document.get("baseFrameSha256") not in (None, current_frames_sha):
        report = {
            "schemaVersion": 1,
            "project": root.name,
            "result": "stale-accepted-set",
            "acceptedBaseFrameSha256": accepted_document.get("baseFrameSha256"),
            "currentFrameSha256": current_frames_sha,
            "explanation": "The accepted change set was already applied (or the frames changed since it was "
                           "written), so there is nothing left to rehearse. Re-run against a fresh draft.",
            "realProjectUntouched": True,
        }
        report_path = project / "qa" / "merge-rehearsal.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if scratch.exists():
        shutil.rmtree(scratch)
    (scratch / "project" / "review").mkdir(parents=True, exist_ok=True)
    (scratch / "deliverables" / "review").mkdir(parents=True, exist_ok=True)
    copies = {
        project / "frames.json": scratch / "project" / "frames.json",
        accepted_source: scratch / "project" / "review" / "accepted-changes.json",
    }
    for optional in (project / "review" / "assisted-review-audit.json", project / "review" / "draft-manifest.json",
                     project / "particle-functions.json"):
        if optional.is_file():
            copies[optional] = scratch / "project" / optional.relative_to(project)
    manifest_path = project / "input-manifest.json"
    slug = load(manifest_path).get("slug", root.name) if manifest_path.is_file() else root.name
    review_markdown = root / "deliverables" / "review" / f"{slug}-review.md"
    if review_markdown.is_file():
        copies[review_markdown] = scratch / "deliverables" / "review" / review_markdown.name
    for source, target in copies.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    merge = subprocess.run([
        sys.executable, str(SCRIPTS / "apply_review_merge.py"),
        "--project-root", str(scratch), "--accepted", str(scratch / "project" / "review" / "accepted-changes.json"),
        "--user-wording", "REHEARSAL-ONLY wording, never a real approval",
        "--source", str(accepted_source),
    ], capture_output=True, text=True)
    refresh = subprocess.run([sys.executable, str(SCRIPTS / "refresh_after_merge.py"),
                              "--project-root", str(scratch), "--slug", slug], capture_output=True, text=True)
    rerun = subprocess.run([
        sys.executable, str(SCRIPTS / "apply_review_merge.py"),
        "--project-root", str(scratch), "--user-wording", "REHEARSAL-ONLY repeat",
    ], capture_output=True, text=True)

    accepted = load(accepted_source)
    expected_deletions = sum(max(0, len(operation.get("indices", [])) - 1)
                             for operation in accepted.get("operations", []) if operation.get("op") == "mergeCards")
    before_cards = sum(len(frame.get("grammarCards", [])) for frame in load(project / "frames.json")["frames"])
    scratch_frames = scratch / "project" / "frames.json"
    after_cards = sum(len(frame.get("grammarCards", [])) for frame in load(scratch_frames)["frames"]) if scratch_frames.is_file() else None
    decision_path = scratch / "project" / "review" / "review-decision.json"
    merge_log_path = scratch / "project" / "review" / "merge-log.json"
    merge_log = load(merge_log_path) if merge_log_path.is_file() else {}
    decision = load(decision_path) if decision_path.is_file() else {}

    checks = {
        "mergeSucceeded": merge.returncode == 0,
        "refreshSucceeded": refresh.returncode == 0,
        "rerunRejected": rerun.returncode != 0,
        "cardCountMatchesMerges": after_cards == before_cards - expected_deletions,
        "mergeLogBoundToNewFrames": merge_log.get("framesAfterSha256") == (sha(scratch_frames) if scratch_frames.is_file() else None),
        "mergeLogBoundToOldFrames": merge_log.get("framesBeforeSha256") == before["project/frames.json"],
        "decisionApprovedWithoutRenderRights": decision.get("content") == "approved" and decision.get("renderAuthorized") is False,
        "decisionBoundToNewFrames": decision.get("frameSha256") == (sha(scratch_frames) if scratch_frames.is_file() else None),
        "realProjectUntouched": {name: sha(root / name) if (root / name).is_file() else None for name in GUARDED} == before,
    }
    report = {
        "schemaVersion": 1,
        "project": root.name,
        "result": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "beforeCards": before_cards,
        "afterCards": after_cards,
        "expectedCardDeletions": expected_deletions,
        "mergeStdout": merge.stdout.strip(),
        "refreshStdout": refresh.stdout.strip(),
        "rerunMessage": (rerun.stdout + rerun.stderr).strip()[:300],
        "scratch": str(scratch.relative_to(root)).replace("\\", "/") if scratch.is_relative_to(root) else str(scratch),
        "note": "Rehearsal only: no approval is claimed and the real project files were proven byte-identical.",
    }
    report_path = project / "qa" / "merge-rehearsal.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
