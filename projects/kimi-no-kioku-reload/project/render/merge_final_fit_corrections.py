"""Merge independently audited final-fit corrections authorized by the user."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
PROPOSALS = [
    PROJECT / "proposals/grammar-final-fit-corrections.json",
    PROJECT / "proposals/translation-final-fit-corrections.json",
]

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pieces(path):
    normalized = re.sub(r"\[(\d+)\]", r".\1", path)
    return [int(part) if part.isdigit() else part for part in normalized.split(".")]

def get(obj, path):
    cur = obj
    for part in pieces(path):
        cur = cur[part]
    return cur

def set_value(obj, path, value):
    path_pieces = pieces(path)
    cur = obj
    for part in path_pieces[:-1]:
        cur = cur[part]
    cur[path_pieces[-1]] = value

before = sha(FRAMES)
expected = "7c0c8d02c6c94d9c80cce49dcab8ffdcf630ef9f288ed00246aa2db013e69ed4"
if before != expected:
    raise RuntimeError(f"Unexpected frames base: {before}")
document = load(FRAMES)
frames = {frame["id"]: frame for frame in document["frames"]}
merged = []
for proposal_path in PROPOSALS:
    proposal = load(proposal_path)
    if proposal["baseFrameSha256"] != before:
        raise RuntimeError(f"Stale proposal: {proposal_path}")
    for index, change in enumerate(proposal["changes"]):
        frame = frames[change["frameId"]]
        if get(frame, change["field"]) != change["old"]:
            raise RuntimeError(f"Old-value mismatch: {proposal_path.name}[{index}]")
        set_value(frame, change["field"], copy.deepcopy(change["new"]))
        merged.append({"proposal": proposal_path.name, "changeIndex": index, "frameId": change["frameId"], "field": change["field"]})
if len(merged) != 13:
    raise RuntimeError(f"Expected 13 corrections, got {len(merged)}")
write(FRAMES, document)
after = sha(FRAMES)
write(PROJECT / "review/final-fit-merge-log.json", {
    "schemaVersion": 1,
    "userWording": "采纳全部提案",
    "framesBeforeSha256": before,
    "framesAfterSha256": after,
    "mergedChangeCount": len(merged),
    "integrationReport": "project/review/final-fit-integration-report.json",
    "merged": merged,
})
print(json.dumps({"merged": len(merged), "before": before, "after": after}, ensure_ascii=False))
