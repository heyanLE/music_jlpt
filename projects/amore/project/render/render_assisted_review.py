"""Render proposal-only Markdown for human review; this never mutates frames.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "project"
OUT = ROOT / "deliverables" / "review" / "amore-assisted-review.md"


def main() -> None:
    frames = {frame["id"]: frame for frame in json.loads((P / "frames.json").read_text(encoding="utf-8"))["frames"]}
    proposals = []
    for path in sorted((P / "proposals").glob("assisted-review-*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        proposals.extend(doc.get("proposals", doc.get("items", [])))
    proposals.sort(key=lambda item: int(item["frameId"][1:]))
    if len({item["frameId"] for item in proposals}) != len(frames):
        raise RuntimeError("Expected exactly one assisted proposal for every frame")
    lines = ["# Amore｜智能词卡审核建议", "", "本文件只展示三组智能审核建议；尚未写入 `frames.json`。可按帧号指出修改，或明确回复“整体采纳”后再合并。助词展示功能而非字典义；英文不生成词卡、假名或罗马音。", ""]
    for item in proposals:
        frame = frames[item["frameId"]]; current = frame["caption"]
        lines += [f"## {item['frameId']}　{frame['startMs'] / 1000:06.2f}", f"歌词：{current['japanese']}", f"暂定中文：{item.get('newTranslationZh', current['translationZh'])}", "", "待核词卡："]
        for card in item.get("suggestedCards", []):
            meaning = card.get("functionZh", card.get("zhMeaning", "待审"))
            source = f"｜原词：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines += [f"- `{card['token']}`｜{card.get('reading', '')}｜{card.get('romaji', '')}{source}", f"  - 含义/功能：{meaning}", f"  - 词性：{card.get('posZh', '待审')}"]
        evidence = item.get("evidence", [])
        if isinstance(evidence, str): evidence = [evidence]
        lines += [f"- 置信度：{item.get('confidence', '待审')}", f"- 分词结构变更：{'是' if item.get('changesTokenStructure') else '否'}"]
        if evidence: lines.append(f"- 依据：{'；'.join(evidence)}")
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


if __name__ == "__main__": main()
