"""Export the full-card rebuild as a compact, human-reviewable Markdown file."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "project" / "review" / "full-card-proposed-frames.json"
OUTPUT = ROOT / "deliverables" / "review" / "zattou-bokura-no-machi-v2-full-card-proposed-review.md"


def card_gloss(card: dict) -> str:
    return card.get("functionZh") or card.get("zhMeaning") or "待人工核对"


def main() -> None:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    lines = [
        "# 雑踏、僕らの街｜全量词卡重建审阅",
        "",
        "此文件为多角色交叉审核后的提案，尚未合并到正式帧数据。QQ 音乐元数据段已排除；每句均已通过词条拼接覆盖校验。",
        "",
        "词卡格式：`词条｜读音｜罗马音｜中文含义／助词功能｜词性`。",
        "",
    ]
    for frame in payload["frames"]:
        caption = frame["caption"]
        lines.extend([
            f"## {frame['id']}  {caption['japanese']}",
            "",
            f"- 整句中文：{caption.get('translationZh') or '待人工核对'}",
            "- 词卡：",
        ])
        for card in frame.get("grammarCards", []):
            lines.append(
                "  - " + "｜".join([
                    card.get("token", ""),
                    card.get("reading", ""),
                    card.get("romaji", ""),
                    card_gloss(card),
                    card.get("posZh", "待人工核对"),
                ])
            )
        lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "frames": len(payload["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
