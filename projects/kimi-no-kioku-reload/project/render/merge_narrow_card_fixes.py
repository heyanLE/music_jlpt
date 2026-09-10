"""Apply meaning-preserving abbreviations for the four narrowest card rows."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "project/frames.json"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

before = sha(FRAMES)
expected = "90f9ee34c6165d151bbb69269e1f8e25603f9c27f4f67ea222e02c3debc73f95"
if before != expected:
    raise RuntimeError(f"Unexpected frames base: {before}")
document = json.loads(FRAMES.read_text(encoding="utf-8"))
changes = []
for frame in document["frames"]:
    if frame["id"] in {"l032", "l055"}:
        for card in frame["grammarCards"]:
            if card["token"] == "と":
                old = card["functionZh"]
                card["functionZh"] = "认定：无可替代的时光"
                changes.append({"frameId": frame["id"], "token": "と", "old": old, "new": card["functionZh"]})
            if card["token"] == "に":
                old = card["functionZh"]
                card["functionZh"] = "构成「ずに」：不……就"
                changes.append({"frameId": frame["id"], "token": "に", "old": old, "new": card["functionZh"]})
    if frame["id"] in {"l038", "l061"}:
        for card in frame["grammarCards"]:
            if card["token"] == "って":
                old = card["functionZh"]
                card["functionZh"] = "表示无论何时"
                changes.append({"frameId": frame["id"], "token": "って", "old": old, "new": card["functionZh"]})
if len(changes) != 10:
    raise RuntimeError(f"Expected 10 narrow-card fixes, got {len(changes)}")
FRAMES.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
after = sha(FRAMES)
log = ROOT / "project/review/narrow-card-fix-log.json"
log.write_text(json.dumps({"schemaVersion": 1, "framesBeforeSha256": before, "framesAfterSha256": after, "changes": changes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"changed": len(changes), "before": before, "after": after}, ensure_ascii=False))
