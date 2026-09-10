#!/usr/bin/env python3
"""Seal mandatory multi-agent review artifacts before the user's content decision."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_ROLES = {"lexical", "grammar", "translation"}


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


def resolve_inside(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Review artifact must be inside the project root: {path}") from exc
    if not path.is_file():
        raise ValueError(f"Review artifact is missing: {path}")
    return path


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--proposal", action="append", required=True, metavar="ROLE=FILE")
    parser.add_argument("--integration", required=True)
    args = parser.parse_args()

    root = args.project_root.resolve(); project = root / "project"
    frames_path = project / "frames.json"
    if not frames_path.is_file():
        raise SystemExit("project/frames.json is missing")
    base_frame_sha = sha(frames_path)

    proposals = []
    seen_roles = set()
    for item in args.proposal:
        if "=" not in item:
            raise SystemExit(f"Invalid --proposal {item!r}; use ROLE=FILE")
        role, value = item.split("=", 1); role = role.strip()
        if role not in REQUIRED_ROLES:
            raise SystemExit(f"Unknown review role: {role}")
        path = resolve_inside(root, value.strip()); document = load(path)
        # Proposal generators may add a scope suffix such as
        # ``lexical-full-coverage``.  The leading role remains canonical.
        declared_role = str(document.get("reviewRole", ""))
        canonical_role = declared_role.split("-", 1)[0]
        if canonical_role != role:
            raise SystemExit(f"Proposal role mismatch in {path}: expected {role}")
        proposal_base = document.get("baseFrameSha256") or document.get("framesSha256") or document.get("frameSha256")
        if proposal_base != base_frame_sha:
            raise SystemExit(f"Proposal is stale for the current draft: {path}")
        if not isinstance(document.get("changes", document.get("proposals")), list):
            raise SystemExit(f"Proposal must contain a changes/proposals list: {path}")
        proposals.append({"role": role, "file": relative(root, path), "sha256": sha(path)})
        seen_roles.add(role)
    if seen_roles != REQUIRED_ROLES:
        raise SystemExit(f"Required roles missing: {sorted(REQUIRED_ROLES - seen_roles)}")

    integration_path = resolve_inside(root, args.integration); integration = load(integration_path)
    if integration.get("reviewRole") != "integration" or integration.get("status") != "completed":
        raise SystemExit("Integration report must have reviewRole=integration and status=completed")
    integration_base = integration.get("baseFrameSha256") or integration.get("framesSha256") or integration.get("frameSha256")
    if integration_base != base_frame_sha:
        raise SystemExit("Integration report is stale for the current draft")

    output = project / "review" / "assisted-review-audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    audit = {
        "schemaVersion": 1,
        "mode": "mandatory-multi-agent",
        "status": "completed",
        "sealedAt": datetime.now(timezone.utc).isoformat(),
        "baseFrameSha256": base_frame_sha,
        "roles": sorted(REQUIRED_ROLES),
        "proposalFiles": proposals,
        "integration": {"file": relative(root, integration_path), "sha256": sha(integration_path)},
        "next": "explicit-user-content-decision",
    }
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    load(output)
    print(json.dumps({"output": str(output), "roles": audit["roles"], "proposalFiles": len(proposals)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
