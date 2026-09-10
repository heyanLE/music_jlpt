from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frames_path = PROJECT / "frames.json"
    backup = PROJECT / "review" / "frames-before-full-card-rebuild.json"
    backup.write_bytes(frames_path.read_bytes())
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    for frame in data["frames"]:
        frame["grammarCards"] = []
        frame["caption"]["furigana"] = []
        frame["status"] = "draft-rebuild"
        frame["fieldProvenance"] = {
            "japanese": "timing/qm.json",
            "romaji": "timing/roma.json",
            "translationZh": "timing/translation.json (QMTS)",
            "grammarCards": "full-card-rebuild-pending",
            "furigana": "full-card-rebuild-pending",
        }
    data["rebuild"] = {
        "reason": "user requested full card regeneration in historical review format",
        "requestedAt": datetime.now(timezone.utc).isoformat(),
        "metadataPolicy": "QRC metadata rows l001-l005 excluded",
    }
    frames_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for folder in (PROJECT / "proposals", PROJECT / "review"):
        for name in ("lexical.json", "grammar.json", "translation.json", "integration-report.json", "assisted-review-audit.json", "merge-log.json", "review-decision.json"):
            source = folder / name
            if source.exists():
                source.rename(source.with_suffix(source.suffix + ".superseded-full-card-rebuild"))
    state = json.loads((PROJECT / "build-state.json").read_text(encoding="utf-8"))
    state["stage"] = "draft_ready"
    state["renderAuthorization"] = False
    state["notes"] = ["Previous card review superseded by requested full-card rebuild.", f"Previous frames backup: {backup.relative_to(ROOT).as_posix()}", f"Current draft frame SHA256: {sha(frames_path)}"]
    (PROJECT / "build-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"backup": str(backup), "frames": len(data["frames"]), "sha256": sha(frames_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
