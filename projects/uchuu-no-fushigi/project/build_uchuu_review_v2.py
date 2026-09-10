import json
from pathlib import Path

ROOT = Path(__file__).parent
data = json.loads((ROOT / "uchuu.frames.approved.json").read_text(encoding="utf-8"))
lines = ["# うちゅうのふしぎ｜已审核词卡", "", "此版本保留已确认的人工审核内容；V2 只更新视觉与显示规范。", ""]
for frame in data["frames"]:
    if frame.get("kind") != "lyric":
        continue
    cap = frame["caption"]
    lines += [f"## {frame['id']} · {frame['startMs'] / 1000:.3f}s", "", f"日文：{cap['japanese']}", f"中文：{cap['translationZh']}", "", "词卡："]
    for item in frame["grammarCards"]:
        lines += [f"- `{item['token']}`｜{item['reading']}｜{item['romaji']}", f"  - 含义/功能：{item.get('functionZh', item['zhMeaning'])}", f"  - 词性：{item['posZh']}"]
    lines.append("")
(ROOT.parent / "deliverables" / "uchuu-review-v2.md").write_text("\n".join(lines), encoding="utf-8")
