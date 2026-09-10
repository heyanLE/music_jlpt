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
    (PROJECT / "review" / "review-decision.json").write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    state_path = PROJECT / "build-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update({"stage": "review_approved", "renderAuthorization": False})
    state.setdefault("notes", []).append("All sealed multi-role proposals accepted; explicit render authorization still required.")
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"content": "approved", "frameSha256": decision["frameSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
