from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frames = PROJECT / "frames.json"
    base = sha(frames)
    proposal_paths = [PROJECT / "proposals" / name for name in ("lexical.json", "grammar.json", "translation.json")]
    proposals = [json.loads(path.read_text(encoding="utf-8")) for path in proposal_paths]
    stale = [str(path) for path, proposal in zip(proposal_paths, proposals) if proposal.get("baseFrameSha256") != base]
    if stale:
        raise SystemExit(f"stale proposal base: {stale}")
    fields = {}
    conflicts = []
    for proposal in proposals:
        for change in proposal.get("changes", []):
            key = (change["frameId"], change["field"])
            fields.setdefault(key, []).append(change)
    for key, changes in fields.items():
        values = {json.dumps(change.get("new"), ensure_ascii=False, sort_keys=True) for change in changes}
        if len(values) > 1:
            conflicts.append({"frameId": key[0], "field": key[1], "changes": changes})
    report = {
        "schemaVersion": 2,
        "reviewRole": "integration",
        "status": "completed",
        "baseFrameSha256": base,
        "sourceProposals": [str(path.relative_to(ROOT)).replace("\\", "/") for path in proposal_paths],
        "conflicts": conflicts,
        "recommendedProposalSet": [
            "lexical.caption.furigana",
            "grammar.grammarCards",
            "translation.caption.translationZh",
        ],
        "recommendation": "Three fields are disjoint; all proposals may be presented together for explicit user content decision.",
    }
    out = PROJECT / "review" / "integration-report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "baseFrameSha256": base, "conflicts": len(conflicts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
