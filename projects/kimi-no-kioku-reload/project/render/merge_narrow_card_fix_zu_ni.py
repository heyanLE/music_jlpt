"""Shorten the repeated ずに function label without changing its meaning."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "project/frames.json"
before = hashlib.sha256(FRAMES.read_bytes()).hexdigest()
if before != "2e27832fc4e02806ba42805109994cd03f7fe4081b8e7fc422c2235003693032":
    raise RuntimeError(f"Unexpected frames base: {before}")
document = json.loads(FRAMES.read_text(encoding="utf-8"))
changes = []
for frame in document["frames"]:
    if frame["id"] not in {"l032", "l055"}:
        continue
    for card in frame["grammarCards"]:
        if card["token"] == "に":
            old = card["functionZh"]
            card["functionZh"] = "构成「ずに」：不……就"
            changes.append({"frameId": frame["id"], "old": old, "new": card["functionZh"]})
if len(changes) != 2:
    raise RuntimeError(f"Expected 2 fixes, got {len(changes)}")
FRAMES.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
after = hashlib.sha256(FRAMES.read_bytes()).hexdigest()
log = ROOT / "project/review/narrow-card-zu-ni-fix-log.json"
log.write_text(json.dumps({"schemaVersion": 1, "framesBeforeSha256": before, "framesAfterSha256": after, "changes": changes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"changed": 2, "before": before, "after": after}, ensure_ascii=False))
