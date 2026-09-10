from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "project" / "frames.json"
OUTPUT = ROOT / "deliverables" / "review" / "dare-ni-mo-narenai-watashi-dakara-v3-confirmed-review.md"


def main() -> None:
    data = json.loads(FRAMES.read_text(encoding="utf-8"))
    lines = ["# 誰にもなれない私だから｜已确认词卡", "", "以下为已合并到正式 frames.json 的内容。", ""]
    for frame in data["frames"]:
        caption = frame["caption"]
        lines.extend([f"## {frame['id']}  {caption['japanese']}", "", f"- 整句中文：{caption.get('translationZh', '')}", "- 词卡："])
        for card in frame["grammarCards"]:
            lines.append("  - " + "｜".join([card.get("token", ""), card.get("reading", ""), card.get("romaji", ""), card.get("functionZh") or card.get("zhMeaning", ""), card.get("posZh", "")]))
        lines.append("")
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(OUTPUT), "frames": len(data["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
