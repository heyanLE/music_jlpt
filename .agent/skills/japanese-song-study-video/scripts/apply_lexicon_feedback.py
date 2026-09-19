#!/usr/bin/env python3
"""Turn the user's review outcome into lexicon reliability feedback.

The lexicon is only useful if it learns: an entry the user accepted should be
reused more confidently next time, an entry they corrected or rejected should be
reused less (or not at all) until it is re-reviewed.

Input (authored by the coordinator from the user's actual decision):

    {
      "project": "eternel",
      "wording": "1. 采纳 3.换成新的 4.渲染",
      "entries": [
        {"surface": "結んで", "outcome": "accepted"},
        {"surface": "で", "outcome": "corrected", "field": "meaning",
         "newValue": "提示动作的共同参与者", "context": "二人で"},
        {"surface": "遠方", "outcome": "rejected", "reason": "wrong gloss for this line"}
      ]
    }

Effects written to lexicon/feedback.json (counters) and lexicon/overrides.json
(reviewed values). build_lexicon.py then folds both into the published lexicon.
Nothing is applied unless --apply is given.

Usage
    python apply_lexicon_feedback.py WORKSPACE_ROOT --decisions FILE [--apply]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTCOMES = ("accepted", "corrected", "rejected")
CORRECTABLE_FIELDS = ("meaning", "grammar", "reading", "romaji", "kind")


def load(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace_root", type=Path)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-new", action="store_true",
                        help="Permit feedback for a surface that is not in the published lexicon (default: refuse, "
                             "so a typo cannot create a phantom entry)")
    args = parser.parse_args()

    root = args.workspace_root.resolve()
    decisions = json.loads(args.decisions.read_text(encoding="utf-8"))
    feedback_path = root / "lexicon" / "feedback.json"
    overrides_path = root / "lexicon" / "overrides.json"
    lexicon_path = root / "lexicon" / "lexicon.json"
    known_surfaces = set()
    if lexicon_path.is_file():
        known_surfaces = {entry["surface"] for entry in json.loads(lexicon_path.read_text(encoding="utf-8"))["entries"]}
    if not args.allow_new and known_surfaces:
        unknown = sorted({str(entry["surface"]).strip() for entry in decisions.get("entries", [])} - known_surfaces)
        if unknown:
            raise SystemExit(f"{len(unknown)} surface(s) are not in the lexicon: {unknown[:5]}; "
                             "pass --allow-new to record them anyway")
    feedback = load(feedback_path, {"schemaVersion": 1, "entries": {}, "log": []})
    overrides = load(overrides_path, {"schemaVersion": 1, "note": "Reviewed values pinned by the user's decisions.", "entries": {}})

    now = datetime.now(timezone.utc).isoformat()
    applied = {"accepted": 0, "corrected": 0, "rejected": 0}
    for entry in decisions.get("entries", []):
        surface = str(entry["surface"]).strip()
        outcome = entry["outcome"]
        if outcome not in OUTCOMES:
            raise SystemExit(f"Unknown outcome {outcome!r} for {surface}")
        bucket = feedback["entries"].setdefault(surface, {"accepts": 0, "rejects": 0, "corrections": 0})
        if outcome == "accepted":
            bucket["accepts"] += 1
        elif outcome == "rejected":
            bucket["rejects"] += 1
        else:
            field = entry.get("field")
            if field not in CORRECTABLE_FIELDS:
                raise SystemExit(f"Correction for {surface} needs one of {CORRECTABLE_FIELDS}")
            # A correction is its own signal. Counting it as an accept would silently
            # clear the net-rejection cap, which is exactly what keeps a bad entry out
            # of automatic reuse.
            bucket["corrections"] += 1
            # A correction is recorded as an additional attested value, never as a
            # global replacement: a particle such as で legitimately carries many
            # functions, so overwriting its dominant value would destroy the entry.
            pinned = overrides["entries"].setdefault(surface, {})
            pinned.setdefault("corrections", []).append({
                "field": field, "value": entry["newValue"], "context": entry.get("context"),
                "project": decisions.get("project"), "at": now,
            })
        applied[outcome] += 1
        feedback["log"].append({
            "at": now, "project": decisions.get("project"), "surface": surface, "outcome": outcome,
            "field": entry.get("field"), "newValue": entry.get("newValue"), "context": entry.get("context"),
            "reason": entry.get("reason"),
        })
    feedback["lastUpdatedAt"] = now
    feedback["lastDecisionWording"] = decisions.get("wording")

    # A rejected entry must stop auto-reusing until it is re-reviewed, and an entry the
    # user has since accepted more often than rejected must recover.
    for surface, bucket in feedback["entries"].items():
        if bucket["rejects"] > bucket["accepts"]:
            overrides["entries"].setdefault(surface, {})["reliability"] = 0.3
        elif bucket["accepts"] > bucket["rejects"] or bucket["corrections"]:
            overrides["entries"].get(surface, {}).pop("reliability", None)

    summary = {
        "project": decisions.get("project"),
        "applied": applied,
        "feedbackEntries": len(feedback["entries"]),
        "pinnedOverrides": len(overrides["entries"]),
        "wrote": [],
    }
    if args.apply:
        write(feedback_path, feedback)
        write(overrides_path, overrides)
        summary["wrote"] = [str(feedback_path.relative_to(root)).replace("\\", "/"), str(overrides_path.relative_to(root)).replace("\\", "/")]
        summary["next"] = "run build_lexicon.py to fold the feedback into lexicon/lexicon.json"
    else:
        summary["dryRun"] = True
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
