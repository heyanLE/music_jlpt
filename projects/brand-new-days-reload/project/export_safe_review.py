"""Export the clean review artifact without relying on terminal encoding."""
import json
from pathlib import Path

ROOT, OUT = Path(__file__).parent, Path(__file__).parent.parent / "deliverables"
data = json.loads((ROOT / "frames.reviewed.safe.json").read_text(encoding="utf-8"))
lines = [
    "# Brand New Days -Reload-｜重新生成的词卡审核",
    "",
    "状态：已从干净 QQ Music 数据重建。l001–l016 已安全导入多角色审核；其余句子保留草稿，等待继续安全导入。",
    "",
]
for frame in data["frames"]:
    lines.extend([f"## {frame['id']}　{frame['startMs']/1000:06.2f}", f"日文：{frame['caption']['japanese']}", f"暂定中文：{frame['caption']['translationZh']}", "", "待核词卡："])
    for card in frame["grammarCards"]:
        meaning = card.get("functionZh", card.get("zhMeaning", "待审"))
        lines.extend([f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}", f"  - 暂定：{meaning}", f"  - 词性：{card['posZh']}"])
    lines.append("")
(OUT / "brand-new-days-review-clean.md").write_text("\n".join(lines), encoding="utf-8")
print("exported", len(data["frames"]), "frames")
