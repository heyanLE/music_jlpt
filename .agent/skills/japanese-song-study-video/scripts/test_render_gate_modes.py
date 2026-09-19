#!/usr/bin/env python3
"""Regression tests for the two review-audit modes of the render gate.

Each case builds a throwaway project independently and asserts whether
``verify_review_gate`` accepts or blocks it. The lexicon mode must stop every way
of satisfying the gate without actually reviewing the queued spans - a gate that
only compares hashes lets an empty or hand-written review through, which removes
the review obligation entirely.

Run:  python test_render_gate_modes.py [--keep]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_render_gate import verify_review_gate  # noqa: E402
from seal_lexicon_review import main as _unused  # noqa: E402,F401 - import check only


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_project(base: Path, *, units: int = 2, cards: int = 3) -> Path:
    root = base / "projects" / "sandbox"
    project = root / "project"
    frames = [{
        "id": "l001", "startMs": 1000, "endMs": 2000,
        "caption": {"japanese": "あした きみと", "furigana": [], "translationZh": "明天与你"},
        "grammarCards": [{"token": f"t{index}", "reading": "よみ", "romaji": "yomi",
                          "zhMeaning": "义", "grammarStructureZh": "名词"} for index in range(cards)],
    }]
    write(project / "frames.json", {"schemaVersion": 3, "frames": frames})
    write(project / "input-manifest.json", {"schemaVersion": 4, "slug": "sandbox", "music": {"asset": "source/music.flac"}})
    queue_units = [{"kind": "unmatched", "text": f"unit{index}", "start": index, "end": index + 1}
                   for index in range(units)]
    write(project / "review" / "rag-review-queue.json", {
        "schemaVersion": 1,
        "lexiconSha256": "a" * 64,
        "totals": {"frames": 1, "cardsDrafted": cards, "lowConfidenceProposed": 0, "reviewUnits": units},
        "queue": [{"frameId": "l001", "japanese": "あした きみと", "units": queue_units}] if units else [],
    })
    return root


def seal_audit(root: Path, review: dict, *, mode: str = "lexicon-rag-targeted-online",
               roles=("online",), queue_file: str = "project/review/rag-review-queue.json",
               review_file: str = "project/review/online-review.json",
               coverage: dict | None = None, content: dict | None = None) -> None:
    project = root / "project"
    queue_path = root / queue_file
    review_path = root / review_file
    write(review_path, review)
    write(project / "review" / "assisted-review-audit.json", {
        "schemaVersion": 2, "mode": mode, "status": "completed", "sealedAt": "2026-01-01T00:00:00Z",
        "baseFrameSha256": sha(project / "frames.json"),
        "roles": list(roles),
        "lexicon": {"path": "lexicon/lexicon.json", "sha256": "a" * 64},
        "ragQueue": {"file": queue_file, "sha256": sha(queue_path), "totals": load(queue_path)["totals"]},
        "onlineReview": {"file": review_file, "sha256": sha(review_path), "changes": len(review.get("changes", []))},
        "coverage": coverage if coverage is not None else load(queue_path).get("totals", {}),
        "content": content if content is not None else {"frames": 1, "cards": len(load(project / "frames.json")["frames"][0]["grammarCards"])},
        "next": "explicit-user-content-decision",
    })


def finish(root: Path, *, user_wording: str = "采纳全部提案", content: str = "approved") -> None:
    project = root / "project"
    frames_sha = sha(project / "frames.json")
    audit_sha = sha(project / "review" / "assisted-review-audit.json")
    merge_log = {"schemaVersion": 2, "framesBeforeSha256": frames_sha, "framesAfterSha256": frames_sha,
                 "scope": "all", "appliedOperations": []}
    write(project / "review" / "merge-log.json", merge_log)
    write(project / "review" / "review-decision.json", {
        "schemaVersion": 2, "content": content, "scope": "all", "renderAuthorized": False,
        "userWording": user_wording, "wordingIsVerbatim": True, "frameSha256": frames_sha,
        "assistedReviewAuditSha256": audit_sha, "mergeLogSha256": sha(project / "review" / "merge-log.json"),
    })


def run_case(name: str, expect: str, builder, keep: bool) -> dict:
    base = Path(tempfile.mkdtemp(prefix="gate-test-"))
    try:
        root = builder(base)
        try:
            verify_review_gate(root)
            outcome, detail = "accept", ""
        except Exception as exc:  # noqa: BLE001 - the message is the evidence
            outcome, detail = "block", f"{type(exc).__name__}: {exc}"
        return {"case": name, "expect": expect, "outcome": outcome,
                "ok": outcome == expect, "detail": detail[:180]}
    finally:
        if not keep:
            shutil.rmtree(base, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    def honest(base: Path) -> Path:
        root = make_project(base, units=2, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义；名词"},
                                      {"frameId": "l001", "unit": "unit1", "resolution": "义；名词"}]})
        finish(root)
        return root

    def empty_review(base: Path) -> Path:
        root = make_project(base, units=2, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed", "changes": []},
                   coverage={"frames": 1, "reviewUnits": 2, "checkedUnits": 0})
        finish(root)
        return root

    def partial_review(base: Path) -> Path:
        root = make_project(base, units=2, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]})
        finish(root)
        return root

    def foreign_review(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "not-queued", "resolution": "义"}]})
        finish(root)
        return root

    def unknown_frame(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        queue = load(root / "project" / "review" / "rag-review-queue.json")
        queue["queue"][0]["frameId"] = "l999"
        write(root / "project" / "review" / "rag-review-queue.json", queue)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l999", "unit": "unit0", "resolution": "义"}]})
        finish(root)
        return root

    def empty_resolution(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "   "}]})
        finish(root)
        return root

    def review_points_at_manifest(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed", "changes": []},
                   review_file="project/input-manifest.json")
        finish(root)
        return root

    def hand_written_audit(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        write(root / "project" / "review" / "online-review.json", {"reviewRole": "online", "status": "completed",
                                                                  "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]})
        # An audit that never went through the sealer: no roles/coverage/content.
        write(root / "project" / "review" / "assisted-review-audit.json", {
            "mode": "lexicon-rag-targeted-online", "status": "completed",
            "ragQueue": {"file": "project/review/rag-review-queue.json", "sha256": sha(root / "project/review/rag-review-queue.json")},
            "onlineReview": {"file": "project/review/online-review.json", "sha256": sha(root / "project/review/online-review.json")},
        })
        finish(root)
        return root

    def duplicate_roles(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]},
                   roles=("online", "online"))
        finish(root)
        return root

    def no_wording(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]})
        finish(root, user_wording="")
        return root

    def generic_authorization(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]})
        finish(root)
        decision_path = root / "project" / "review" / "review-decision.json"
        decision = load(decision_path)
        decision.pop("userWording")
        decision["authorization"] = "generated"
        write(decision_path, decision)
        return root

    def rehearsal_wording(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]})
        finish(root, user_wording="REHEARSAL-ONLY wording, never a real approval")
        return root

    def zero_card_project(base: Path) -> Path:
        root = make_project(base, units=0, cards=0)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed", "changes": []},
                   coverage={"frames": 1, "reviewUnits": 0, "checkedUnits": 0},
                   content={"frames": 1, "cards": 0})
        finish(root)
        return root

    def audit_not_bound_to_draft(base: Path) -> Path:
        root = make_project(base, units=1, cards=3)
        seal_audit(root, {"schemaVersion": 1, "reviewRole": "online", "status": "completed",
                          "changes": [{"frameId": "l001", "unit": "unit0", "resolution": "义"}]})
        finish(root)
        audit_path = root / "project" / "review" / "assisted-review-audit.json"
        audit = load(audit_path)
        audit["baseFrameSha256"] = "b" * 64
        write(audit_path, audit)
        # keep the decision bound to the mutated audit so only the draft binding is under test
        decision_path = root / "project" / "review" / "review-decision.json"
        decision = load(decision_path)
        decision["assistedReviewAuditSha256"] = sha(audit_path)
        write(decision_path, decision)
        return root

    def multi_agent_honest(base: Path) -> Path:
        root = make_project(base, units=0, cards=3)
        project = root / "project"
        for role in ("lexical", "grammar", "translation"):
            write(project / "review" / "proposals" / f"{role}.json",
                  {"schemaVersion": 2, "reviewRole": role, "status": "completed", "changes": []})
        write(project / "review" / "integration-report.json",
              {"schemaVersion": 2, "reviewRole": "integration", "status": "completed", "changes": []})
        frames_sha = sha(project / "frames.json")
        write(project / "review" / "assisted-review-audit.json", {
            "schemaVersion": 1, "mode": "mandatory-multi-agent", "status": "completed",
            "baseFrameSha256": frames_sha, "roles": ["lexical", "grammar", "translation"],
            "proposalFiles": [{"role": role, "file": f"project/review/proposals/{role}.json",
                               "sha256": sha(project / "review" / "proposals" / f"{role}.json")}
                              for role in ("lexical", "grammar", "translation")],
            "integration": {"file": "project/review/integration-report.json",
                            "sha256": sha(project / "review" / "integration-report.json")},
        })
        finish(root)
        return root

    def multi_agent_missing_role(base: Path) -> Path:
        root = multi_agent_honest(base)
        audit_path = root / "project" / "review" / "assisted-review-audit.json"
        audit = load(audit_path)
        audit["proposalFiles"] = [record for record in audit["proposalFiles"] if record["role"] != "grammar"]
        write(audit_path, audit)
        decision_path = root / "project" / "review" / "review-decision.json"
        decision = load(decision_path)
        decision["assistedReviewAuditSha256"] = sha(audit_path)
        write(decision_path, decision)
        return root

    cases = [
        ("A1 honest lexicon review", "accept", honest),
        ("A2 honest multi-agent review", "accept", multi_agent_honest),
        ("B1 zero-change review over a non-empty queue", "block", empty_review),
        ("B2 review answers only some queued units", "block", partial_review),
        ("B3 review answers a unit that was never queued", "block", foreign_review),
        ("B4 review references an unknown frame", "block", unknown_frame),
        ("B5 review change without a resolution", "block", empty_resolution),
        ("C1 onlineReview.file points at another project file", "block", review_points_at_manifest),
        ("C2 hand-written audit (no sealer fields)", "block", hand_written_audit),
        ("C3 duplicate role entries", "block", duplicate_roles),
        ("D1 decision without userWording", "block", no_wording),
        ("D2 generic authorization instead of the user's wording", "block", generic_authorization),
        ("D3 rehearsal wording", "block", rehearsal_wording),
        ("E1 zero-card project with no declaration", "block", zero_card_project),
        ("E2 audit not bound to the merged draft", "block", audit_not_bound_to_draft),
        ("F1 multi-agent audit missing a role", "block", multi_agent_missing_role),
    ]
    results = [run_case(name, expect, builder, args.keep) for name, expect, builder in cases]
    failures = [result for result in results if not result["ok"]]
    for result in results:
        flag = "OK   " if result["ok"] else "FAIL "
        print(f"[{flag}] {result['case']}: expect={result['expect']} -> {result['outcome']}"
              + (f"  ({result['detail']})" if result["detail"] else ""))
    print(json.dumps({"total": len(results), "failed": len(failures),
                      "failures": [result["case"] for result in failures]}, ensure_ascii=False))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
