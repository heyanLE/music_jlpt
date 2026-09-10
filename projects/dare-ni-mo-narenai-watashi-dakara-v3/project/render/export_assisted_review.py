from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "project" / "review" / "integrated-proposed-frames.json"
OUTPUT = ROOT / "deliverables" / "review" / "dare-ni-mo-narenai-watashi-dakara-v3-assisted-review.md"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    lines = [
        "# 誰にもなれない私だから｜多角色审核词卡提案",
        "",
        "此文件是词汇、文法、翻译三角色交叉审核后的提案，尚未合并到正式帧数据。QRC 元数据行已排除；全部词卡通过逐句拼接覆盖校验。",
        "",
        "词卡格式：`词条｜读音｜罗马音｜中文含义／助词功能｜词性`。",
        "",
    ]
    for frame in payload["frames"]:
        caption = frame["caption"]
        lines.extend([f"## {frame['id']}  {caption['japanese']}", "", f"- 整句中文：{caption.get('translationZh') or '待人工核对'}", "- 词卡："])
        for card in frame.get("grammarCards", []):
            lines.append("  - " + "｜".join([
                card.get("token", ""), card.get("reading", ""), card.get("romaji", ""),
                card.get("functionZh") or card.get("zhMeaning") or "待人工核对",
                card.get("posZh") or card.get("grammarStructureZh") or "待人工核对",
            ]))
        lines.append("")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUTPUT), "frames": len(payload["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
