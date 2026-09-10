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
    decision = {
        "schemaVersion": 2,
        "content": "approved",
        "scope": "all",
        "renderAuthorized": False,
        "userWording": "采纳全部提案",
        "frameSha256": sha(frames),
        "assistedReviewAuditSha256": sha(PROJECT / "review" / "assisted-review-audit.json"),
        "mergeLogSha256": sha(PROJECT / "review" / "merge-log.json"),
    }
    out = PROJECT / "review" / "review-decision.json"
    out.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    state = json.loads((PROJECT / "build-state.json").read_text(encoding="utf-8"))
    state["stage"] = "review_approved"
    state["renderAuthorization"] = False
    state["notes"] = [
        "QRC metadata rows l001-l005 excluded.",
        "All v2 lexical, grammar, and translation proposals accepted by user; 259 cards merged across 61 lyric frames.",
        "Content approved; explicit render authorization still required.",
    ]
    (PROJECT / "build-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"content": "approved", "renderAuthorized": False, "frameSha256": decision["frameSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
