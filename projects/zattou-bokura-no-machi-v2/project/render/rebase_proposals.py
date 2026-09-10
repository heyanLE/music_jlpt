from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frame_path = PROJECT / "frames.json"
    frame_ids = {item["id"] for item in json.loads(frame_path.read_text(encoding="utf-8")).get("frames", [])}
    base = sha(frame_path)
    result = {}
    for role in ("lexical", "grammar", "translation"):
        stale = PROJECT / "proposals" / f"{role}.json.stale-after-metadata-filter"
        source = json.loads(stale.read_text(encoding="utf-8"))
        current = copy.deepcopy(source)
        current["baseFrameSha256"] = base
        current["rebasedFrom"] = str(stale.relative_to(ROOT)).replace("\\", "/")
        current["changes"] = [change for change in source.get("changes", []) if change["frameId"] in frame_ids]
        out = PROJECT / "proposals" / f"{role}.json"
        out.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        result[role] = len(current["changes"])
    log = PROJECT / "review" / "proposal-rebase-log.json"
    log.write_text(json.dumps({"reason": "metadata frames l001-l005 removed", "newBaseFrameSha256": base, "retainedChanges": result, "droppedChanges": {"translation": 5}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"baseFrameSha256": base, "retainedChanges": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
