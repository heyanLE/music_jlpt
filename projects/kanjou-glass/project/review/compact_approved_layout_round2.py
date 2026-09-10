from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"

COMPACTIONS = [
    ("l001", 1, "functionZh", "连接水面与波纹，表示修饰关系", "修饰“波纹”"),
    ("l001", 3, "functionZh", "表示起点：从波纹处移开", "表示移开的起点"),
    ("l001", 6, "functionZh", "将“移开脸”这一小句名词化", "名词化前句"),
    ("l001", 7, "functionZh", "提示名词化小句为主题：之所以…", "提示原因主题"),
    ("l003", 1, "functionZh", "表示共同动作的对象：与你并肩", "表示共同对象"),
    ("l003", 3, "functionZh", "限定：仅仅与你并肩", "表示限定"),
    ("l003", 4, "functionZh", "连接前面的限定小句与心臓，表示连体修饰", "修饰“心臓”"),
    ("l003", 6, "functionZh", "标记跨句主语“心臓”", "标记跨句主语"),
    ("l017", 1, "functionZh", "标记程度从句中的主语：世界", "标记从句主语"),
    ("l017", 5, "zhMeaning", "断定：是美丽的", "表示断定"),
    ("l017", 6, "functionZh", "标记思った的引用内容", "标记引用内容"),
    ("l022", 2, "zhMeaning", "连接样态表达与名词", "连接样态与名词"),
    ("l022", 4, "functionZh", "标记主语：こぼれそうな想い", "标记主语"),
    ("l022", 6, "functionZh", "标记満たす的对象：胸", "标记宾语"),
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
            "reason": "preserve approved function while fitting the fixed one-row card layout",
        })
    write(FRAMES, document)
    after = sha(FRAMES)

    merge_path = PROJECT / "review" / "merge-log.json"
    merge = load(merge_path)
    if merge.get("framesAfterSha256") != before:
        raise SystemExit("Merge log does not point to pre-compaction frames")
    merge.setdefault("postMergeLayoutCompactions", []).extend(log_items)
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
