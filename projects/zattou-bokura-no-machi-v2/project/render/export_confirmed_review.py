from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def main() -> None:
    data = json.loads((PROJECT / "frames.json").read_text(encoding="utf-8"))
    lines = ["# 雑踏、僕らの街｜已合并词卡", "", "QRC 元数据行已排除；以下为当前 frames.json 的已确认内容。", ""]
    for frame in data["frames"]:
        caption = frame["caption"]
        lines += [f"## {frame['id']}｜{caption['japanese']}", "", f"- 整句中文：{caption.get('translationZh', '')}", f"- 罗马音：{caption.get('romaji', '')}", "- 假名："]
        for note in caption.get("furigana", []):
            lines.append(f"  - {note.get('base', '')}：{note.get('reading', '')}")
        lines.append("- 词卡：")
        if not frame.get("grammarCards"):
            lines.append("  - 无词卡（纯英文或本句无提案）")
        else:
            for card in frame["grammarCards"]:
                meaning = card.get("functionZh") or card.get("zhMeaning", "")
                pos = card.get("posZh", "")
                lines.append(f"  - {card.get('token', '')}｜{card.get('reading', '')}｜{card.get('romaji', '')}｜{meaning}｜{pos}")
        lines += [f"- 状态：{frame.get('status', '')}", ""]
    out = ROOT / "deliverables" / "review" / "zattou-bokura-no-machi-v2-review.md"
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(data["frames"]), "output": str(out), "cards": sum(len(f.get("grammarCards", [])) for f in data["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
