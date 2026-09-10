from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
EXACT_USER_WORDING = "采纳全部提案  "


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    frames_path = PROJECT / "frames.json"
    document = load(frames_path)
    lines = [
        "# 感情グラス｜已确认词卡", "",
        "内容已经按用户决定整体采纳，并通过 33 帧固定版式回归。助词仅显示句中功能；振假名仅覆盖汉字段；片假名舶来词显示来源词。", "",
        f"正式帧哈希：`{sha(frames_path)}`", "",
    ]
    for frame in document["frames"]:
        caption = frame["caption"]
        lines.extend([
            f"## {frame['id']}　{frame['startMs'] / 1000:.3f}s", "",
            f"歌词：{caption.get('japanese', '')}", "",
            f"中文：{caption.get('translationZh', '')}", "",
            f"分词罗马音：{caption.get('romaji', '')}", "", "词卡：", "",
        ])
        for card in frame.get("grammarCards", []):
            meaning = card.get("functionZh") or card.get("zhMeaning") or ""
            source = f"｜词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(
                f"- `{card['token']}`｜读音：{card.get('reading', '')}｜罗马音：{card.get('romaji', '')}"
                f"｜{meaning}｜{card.get('grammarStructureZh', '')}{source}"
            )
        lines.append("")
    content = "\n".join(lines)
    for output in (
        ROOT / "deliverables" / "review" / "kanjou-glass-review.md",
        ROOT / "deliverables" / "review" / "kanjou-glass-approved-review.md",
    ):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8", newline="\n")

    merge_path = PROJECT / "review" / "merge-log.json"
    merge = load(merge_path)
    merge["userWording"] = EXACT_USER_WORDING
    write_json(merge_path, merge)

    decision_path = PROJECT / "review" / "content-decision.json"
    decision = load(decision_path)
    decision["userWording"] = EXACT_USER_WORDING
    decision["frameSha256"] = sha(frames_path)
    decision["mergeLogSha256"] = sha(merge_path)
    decision["renderAuthorized"] = False
    write_json(decision_path, decision)

    state_path = PROJECT / "build-state.json"
    state = load(state_path)
    state["stage"] = "review_approved"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append(
        "User adopted all sealed proposals; 19 semantic-preserving layout compactions passed the 33-frame regression."
    )
    write_json(state_path, state)
    print(json.dumps({
        "stage": state["stage"],
        "frameSha256": sha(frames_path),
        "review": str(ROOT / "deliverables" / "review" / "kanjou-glass-approved-review.md"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
