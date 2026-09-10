"""Merge the user-approved, independently audited layout-correction set."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
FILES = {
    "lexical": PROJECT / "proposals/lexical-layout-corrections.json",
    "grammar": PROJECT / "proposals/grammar-layout-corrections.json",
    "translation": PROJECT / "proposals/translation-layout-corrections.json",
}
INCLUDED = {
    "lexical": set(range(3)),
    "grammar": set(range(14)),
    "translation": {0, 1, 2, 3, 5, 6},
}
ALTERNATIVES = {
    ("l032", "grammarCards.4.functionZh"): "标记认定内容：无可替代的时光",
    ("l055", "grammarCards.4.functionZh"): "标记认定内容：无可替代的时光",
}

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def path_parts(path):
    normalized = re.sub(r"\[(\d+)\]", r".\1", path)
    return [int(piece) if piece.isdigit() else piece for piece in normalized.split(".")]

def get(obj, path):
    cur = obj
    for piece in path_parts(path):
        cur = cur[piece]
    return cur

def set_value(obj, path, value):
    pieces = path_parts(path)
    cur = obj
    for piece in pieces[:-1]:
        cur = cur[piece]
    cur[pieces[-1]] = value

before = sha(FRAMES)
expected = "f567e0e1c582104b125ee6e670b6f53ded7689de43f948cc55f00b24749d57de"
if before != expected:
    raise RuntimeError(f"Unexpected frames base: {before}")

document = load(FRAMES)
frames = {frame["id"]: frame for frame in document["frames"]}
merged = []
for role, proposal_path in FILES.items():
    proposal = load(proposal_path)
    if proposal["baseFrameSha256"] != before:
        raise RuntimeError(f"Stale proposal: {proposal_path}")
    for index, change in enumerate(proposal["changes"]):
        if index not in INCLUDED[role]:
            continue
        frame = frames[change["frameId"]]
        actual = get(frame, change["field"])
        if actual != change["old"]:
            raise RuntimeError(f"Old-value mismatch: {role}[{index}]")
        set_value(frame, change["field"], copy.deepcopy(change["new"]))
        merged.append({"role": role, "changeIndex": index, "frameId": change["frameId"], "field": change["field"]})

for (frame_id, field), new_value in ALTERNATIVES.items():
    frame = frames[frame_id]
    old_value = get(frame, field)
    set_value(frame, field, new_value)
    merged.append({"role": "integration", "frameId": frame_id, "field": field, "old": old_value, "new": new_value})

if len(merged) != 25:
    raise RuntimeError(f"Expected 25 merged corrections, got {len(merged)}")
for frame in document["frames"]:
    frame["status"] = "user-approved-reviewed"
    frame["reviewRequired"] = False
write(FRAMES, document)
after = sha(FRAMES)

log = {
    "schemaVersion": 2,
    "userWording": "采纳全部提案",
    "scope": "23 audited layout changes plus 2 meaning-preserving integration alternatives",
    "framesBeforeSha256": before,
    "framesAfterSha256": after,
    "mergedChangeCount": len(merged),
    "merged": merged,
    "integrationReport": "project/review/layout-correction-integration-report.json",
}
write(PROJECT / "review/layout-correction-merge-log.json", log)
print(json.dumps({"merged": len(merged), "before": before, "after": after}, ensure_ascii=False))
