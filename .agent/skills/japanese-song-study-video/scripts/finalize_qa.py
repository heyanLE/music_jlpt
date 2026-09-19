#!/usr/bin/env python3
"""Record the visual QA findings and mark a collect_qa report as passed.

The generic step every project had been re-implementing: after inspecting the
extracted frames, attach the concrete findings to the report and flip its result
from ``pending-visual-review`` to ``passed``, while proving the report still
hashes the candidate that will be promoted.

Usage
    python finalize_qa.py PROJECT_ROOT QA_REPORT --findings FILE [--inspected-by TEXT]
        [--supplementary KEY=PATH ...] [--result passed|failed] [--note TEXT ...]

``--findings`` accepts either a JSON array of strings or a Markdown/text file with
one finding per non-empty line (``-`` or ``*`` bullets are stripped).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_findings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8").strip()
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            raise SystemExit("--findings JSON must be an array of strings")
        return data
    findings = []
    for line in text.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        if stripped and not stripped.startswith("#"):
            findings.append(stripped)
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("qa_report", type=Path)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--inspected-by", default="coordinating agent, direct visual inspection")
    parser.add_argument("--supplementary", action="append", default=[], metavar="KEY=PATH")
    parser.add_argument("--result", choices=("passed", "failed"), default="passed")
    parser.add_argument("--note", action="append", default=[])
    args = parser.parse_args()

    root = args.project_root.resolve()
    report_path = args.qa_report.resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    candidate_value = report.get("candidate")
    if not candidate_value:
        raise SystemExit("QA report has no candidate field")
    candidate = Path(candidate_value)
    if not candidate.is_absolute():
        candidate = root / candidate
    if not candidate.is_file():
        raise SystemExit(f"Candidate is missing: {candidate}")
    current_hash = sha(candidate)
    if report.get("candidateSha256") != current_hash:
        raise SystemExit("QA report does not hash the current candidate; re-run collect_qa.py")
    if report.get("result") == "passed" and args.result == "passed":
        print(json.dumps({"result": "already-passed", "candidateSha256": current_hash}, ensure_ascii=False))
        return

    findings = read_findings(args.findings.resolve())
    if args.result == "passed" and not findings:
        raise SystemExit("Refusing to mark QA passed with no recorded findings")
    supplementary = {}
    for item in args.supplementary:
        if "=" not in item:
            raise SystemExit(f"--supplementary expects KEY=PATH, got {item!r}")
        key, value = item.split("=", 1)
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        supplementary[key] = {"path": str(path.relative_to(root)).replace("\\", "/") if path.is_relative_to(root) else str(path),
                              "sha256": sha(path) if path.is_file() else None,
                              "exists": path.is_file()}

    report["result"] = args.result
    report["inspectedAt"] = datetime.now(timezone.utc).isoformat()
    report["inspectedBy"] = args.inspected_by
    report["visualFindings"] = findings
    if supplementary:
        report["supplementaryChecks"] = supplementary
    if args.note:
        report["notes"] = list(report.get("notes", [])) + args.note
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(report_path.read_text(encoding="utf-8"))
    print(json.dumps({
        "report": str(report_path.relative_to(root)).replace("\\", "/"),
        "result": report["result"],
        "findings": len(findings),
        "screenshots": len(report.get("screenshots", [])),
        "candidateSha256": current_hash,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
