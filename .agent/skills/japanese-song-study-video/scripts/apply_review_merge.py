#!/usr/bin/env python3
"""Apply the accepted review change set to frames.json and record the merge.

Inputs
  project/review/accepted-changes.json   the change set the user accepted
  --user-wording TEXT                    the user's verbatim content decision
  --source FILE (repeatable)             proposal/integration files that fed the merge

Operations
  set         {frameId, field, old, new}          scalar or nested field
  mergeCards  {frameId, indices, expectedTokens, newCard}

Every operation is verified against the recorded old value or expected tokens
before anything is written, so a stale or hand-edited change set fails instead
of silently overwriting reviewed content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

INDEX = re.compile(r"^(?P<name>[A-Za-z_]+)\[(?P<index>\d+)\]$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(container, path: str):
    parts = path.split(".")
    node = container
    for part in parts[:-1]:
        match = INDEX.match(part)
        node = node[match.group("name")][int(match.group("index"))] if match else node[part]
    last = parts[-1]
    match = INDEX.match(last)
    if match:
        collection = node[match.group("name")]
        index = int(match.group("index"))
        return collection, index
    return node, last


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True, help="Project root, e.g. projects/<slug>")
    parser.add_argument("--accepted", type=Path)
    parser.add_argument("--user-wording", required=True)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--scope", default="all 25 frames (l001-l025)")
    parser.add_argument("--content", default="approved")
    args = parser.parse_args()

    project = args.project_root.resolve() / "project"
    frames_path = project / "frames.json"
    before = sha(frames_path)
    frames_doc = load(frames_path)
    accepted_path = args.accepted or (project / "review" / "accepted-changes.json")
    accepted = load(accepted_path)
    if accepted.get("baseFrameSha256") != before:
        raise SystemExit(f"Accepted change set is stale: {accepted.get('baseFrameSha256')} != {before}")

    frames_by_id = {frame["id"]: frame for frame in frames_doc["frames"]}
    applied = []
    for operation in accepted["operations"]:
        frame = frames_by_id.get(operation.get("frameId"))
        if frame is None:
            raise SystemExit(f"Unknown frame: {operation.get('frameId')}")
        kind = operation["op"]
        if kind == "set":
            parent, key = resolve(frame, operation["field"])
            if parent[key] != operation["old"]:
                raise SystemExit(f"Old value mismatch at {operation['frameId']}.{operation['field']}: {parent[key]!r} != {operation['old']!r}")
            parent[key] = operation["new"]
        elif kind == "mergeCards":
            cards = frame["grammarCards"]
            indices = operation["indices"]
            current = [cards[index]["token"] for index in indices]
            if current != operation["expectedTokens"]:
                raise SystemExit(f"Merge precondition failed at {operation['frameId']}: {current} != {operation['expectedTokens']}")
            merged = dict(cards[indices[0]])
            merged.update(operation["newCard"])
            frame["grammarCards"] = [card for position, card in enumerate(cards) if position not in indices]
            frame["grammarCards"].insert(indices[0], merged)
        else:
            raise SystemExit(f"Unsupported operation: {kind}")
        applied.append({"frameId": operation["frameId"], "op": kind, "field": operation.get("field"), "old": operation.get("old"), "new": operation.get("new") or operation.get("newCard"), "reason": operation.get("reason")})

    # The provenance written onto every card must name the review that actually
    # happened. A lexicon-RAG project never ran the three-role pass, so stamping that
    # wording onto its frames would be a false provenance claim in the very record the
    # audit chain relies on.
    audit_path = project / "review" / "assisted-review-audit.json"
    if not audit_path.is_file():
        raise SystemExit(f"Seal the review before merging: {audit_path} is missing")
    card_provenance = ("lexicon RAG draft reviewed online with recorded evidence and accepted by the user"
                       if load(audit_path).get("mode") == "lexicon-rag-targeted-online" else
                       "authored draft reviewed by lexical/grammar/translation agents and accepted by the user")

    confirmed_all = accepted.get("confirmAllFrames") is True
    for frame in frames_doc["frames"]:
        if not frame.get("grammarCards"):
            continue
        frame["status"] = "human-confirmed-cards"
        frame["cardReviewStatus"] = "human-confirmed"
        frame["reviewRequired"] = False
        frame["fieldProvenance"]["grammarCards"] = card_provenance
        frame["fieldProvenance"]["humanConfirmation"] = args.user_wording
        for card in frame["grammarCards"]:
            card["status"] = "human-confirmed"
            card["reviewRequired"] = False
            card["fieldProvenance"]["humanConfirmation"] = args.user_wording
    if not confirmed_all:
        raise SystemExit("Partial acceptance requires per-frame confirmation support; this run expects confirmAllFrames")

    write(frames_path, frames_doc)
    after = sha(frames_path)

    merge_log = {
        "schemaVersion": 2,
        "framesBeforeSha256": before,
        "framesAfterSha256": after,
        "scope": args.scope,
        "appliedOperations": applied,
        "declinedProposals": accepted.get("declined", []),
        "sourceProposals": [
            {"file": value, "sha256": sha(Path(value) if Path(value).is_absolute() else args.project_root.resolve() / value)}
            for value in args.source
        ],
        "confirmedFrames": "all",
    }
    write(project / "review" / "merge-log.json", merge_log)

    wording = args.user_wording.strip()
    decision = {
        "schemaVersion": 2,
        "content": args.content,
        "scope": args.scope,
        "renderAuthorized": False,
        "userWording": wording,
        "wordingIsVerbatim": True,
        "frameSha256": after,
        "assistedReviewAuditSha256": sha(audit_path),
        "mergeLogSha256": sha(project / "review" / "merge-log.json"),
    }
    write(project / "review" / "review-decision.json", decision)
    print(json.dumps({"framesBefore": before, "framesAfter": after, "applied": len(applied)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
