"""Make a user-readable view of the merged, human-confirmed cards."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P, OUT = ROOT / "project", ROOT / "deliverables" / "review" / "amore-review-approved.md"


def main() -> None:
    frames = json.loads((P / "frames.json").read_text(encoding="utf-8"))["frames"]
    lines = ["# Amore｜已确认词卡", "", "本版已按“整体采纳”合并智能审核建议；可继续逐帧提出修订。尚未授权渲染最终视频。", ""]
    for frame in frames:
        cap = frame["caption"]
        lines += [f"## {frame['id']}　{frame['startMs'] / 1000:06.2f}", f"歌词：{cap['japanese']}", f"中文：{cap['translationZh']}", "", "词卡："]
        for card in frame["grammarCards"]:
            meaning = card.get("functionZh", card.get("zhMeaning", "")); source = f"｜原词：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines += [f"- `{card['token']}`｜{card.get('reading', '')}｜{card.get('romaji', '')}{source}", f"  - 含义/功能：{meaning}", f"  - 词性：{card.get('posZh', '')}"]
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__": main()
