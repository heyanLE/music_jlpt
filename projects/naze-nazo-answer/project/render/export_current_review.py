from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
frames = json.loads((ROOT / "project" / "frames.json").read_text(encoding="utf-8"))["frames"]
lines = ["# なぜ？謎？！ANSWER｜当前已确认词卡", "", "本稿同步当前 `frames.json`，包括人工修正：l011/l032 的「まことか」与 l028 的「ひびくかな」。", ""]
for frame in frames:
    lines += [f"## {frame['id']}  {frame['caption']['japanese']}", "", f"- 中文：{frame['caption'].get('translationZh', '')}", "- 词卡："]
    for card in frame["grammarCards"]:
        value = card.get("functionZh", card.get("zhMeaning", ""))
        lines.append(f"  - {card['token']}｜{card['reading']}｜{card['romaji']}｜{value}｜{card['grammarStructureZh']}")
    lines.append("")
out = ROOT / "deliverables" / "review" / "naze-nazo-answer-current-review.md"
out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(out)
