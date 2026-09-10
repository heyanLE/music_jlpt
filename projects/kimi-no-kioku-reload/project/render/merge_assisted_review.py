"""Merge the user-approved integrated recommendation set, excluding audit blocks."""
import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "project"
FRAMES = P / "frames.json"
ROLE_FILES = {role: P / f"proposals/{role}.json" for role in ("lexical", "grammar", "translation")}
EXCLUDED = {"lexical": {4, 5, 19}, "grammar": {20}, "translation": set()}

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def parts(path):
    normalized = re.sub(r"\[(\d+)\]", r".\1", path)
    return [int(piece) if piece.isdigit() else piece for piece in normalized.split(".")]

def get(obj, path):
    cur = obj
    for piece in parts(path):
        cur = cur[piece]
    return cur

def set_value(obj, path, value):
    sequence = parts(path); cur = obj
    for piece in sequence[:-1]: cur = cur[piece]
    cur[sequence[-1]] = value

before = sha(FRAMES)
document = load(FRAMES)
frames = {frame["id"]: frame for frame in document["frames"]}
merged = []
for role, path in ROLE_FILES.items():
    proposal = load(path)
    assert proposal["baseFrameSha256"] == before
    for index, change in enumerate(proposal["changes"]):
        if index in EXCLUDED[role]: continue
        frame = frames[change["frameId"]]
        actual = get(frame, change["field"])
        if actual != change["old"]:
            raise RuntimeError(f"Old-value mismatch {role}[{index}] {change['frameId']} {change['field']}: {actual!r} != {change['old']!r}")
        set_value(frame, change["field"], copy.deepcopy(change["new"]))
        merged.append({"role": role, "changeIndex": index, "frameId": change["frameId"], "field": change["field"]})

assert len(merged) == 429
for frame in document["frames"]:
    frame["status"] = "user-approved-integrated-proposals"
    frame["reviewRequired"] = frame["id"] in {"l008", "l010", "l028", "l042"}
write(FRAMES, document)
after = sha(FRAMES)
audit = P / "review/assisted-review-audit.json"
merge_log = {
    "schemaVersion": 2,
    "userWording": "采纳全部提案",
    "scope": "integration recommendedProposalSet: all-except-listed",
    "framesBeforeSha256": before,
    "framesAfterSha256": after,
    "mergedChangeCount": len(merged),
    "excludedBlockingChanges": {role: sorted(values) for role, values in EXCLUDED.items()},
    "merged": merged,
    "proposalFiles": [{"role": role, "path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)} for role, path in ROLE_FILES.items()],
}
write(P / "review/merge-log.json", merge_log)
decision = {
    "schemaVersion": 2,
    "content": "approved-with-four-audited-corrections-pending",
    "scope": "429 integrated recommended changes",
    "renderAuthorized": False,
    "userWording": "采纳全部提案",
    "frameSha256": after,
    "assistedReviewAuditSha256": sha(audit),
    "mergeLogSha256": sha(P / "review/merge-log.json"),
    "pendingFrames": ["l008", "l010", "l028", "l042"],
}
write(P / "review/review-decision.json", decision)
print(json.dumps({"merged": len(merged), "before": before, "after": after, "pendingFrames": decision["pendingFrames"]}, ensure_ascii=False))
