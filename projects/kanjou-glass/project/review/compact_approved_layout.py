from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"

COMPACTIONS = [
    ("l001", 3, "functionZh", "表示视线离开的起点：从水面波纹处移开脸", "表示起点：从波纹处移开"),
    ("l003", 6, "functionZh", "标记跨句主语“心臓”，谓语为下一句的火照りやまない", "标记跨句主语“心臓”"),
    ("l017", 3, "functionZh", "表示程度：美到仿佛世界都改变", "表示极高程度"),
    ("l022", 1, "grammarStructureZh", "样态助动词（表示即将发生）", "样态助动词"),
    ("l027", 5, "functionZh", "连接状态与评价いい：保持那样也可以", "承接状态并作评价"),
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    before = sha(FRAMES)
    document = load(FRAMES)
    by_id = {frame["id"]: frame for frame in document["frames"]}
    log_items = []
    for frame_id, index, field, old, new in COMPACTIONS:
        card = by_id[frame_id]["grammarCards"][index]
        if card.get(field) != old:
            raise SystemExit(f"Unexpected old value: {frame_id} grammarCards[{index}].{field}")
        card[field] = new
        card.setdefault("fieldProvenance", {})["layoutCompaction"] = "semantic-preserving fixed-layout compaction after user approval"
        log_items.append({
            "frameId": frame_id,
            "field": f"grammarCards[{index}].{field}",
            "old": old,
            "new": new,
            "reason": "preserve approved meaning while fitting the fixed one-row card layout",
        })
    write(FRAMES, document)
    after = sha(FRAMES)

    merge_path = PROJECT / "review" / "merge-log.json"
    merge = load(merge_path)
    if merge.get("framesAfterSha256") != before:
        raise SystemExit("Merge log does not point to pre-compaction frames")
    merge["postMergeLayoutCompactions"] = log_items
    merge["framesAfterSha256"] = after
    write(merge_path, merge)

    decision_path = PROJECT / "review" / "content-decision.json"
    decision = load(decision_path)
    decision["frameSha256"] = after
    decision["mergeLogSha256"] = sha(merge_path)
    write(decision_path, decision)
    print(json.dumps({"compactions": len(log_items), "before": before, "after": after}, ensure_ascii=False))


if __name__ == "__main__":
    main()
