"""Build the deterministic, unapproved card draft for キミの記憶 -Reload-."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(r"C:\project\musicjlpt\projects\kanjou-glass\project\render\build_card_draft.py")
spec = importlib.util.spec_from_file_location("shared_card_draft_base", BASE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

module.ROOT = ROOT
module.PROJECT = ROOT / "project"
module.LOCAL_SITE = module.PROJECT / "work" / "python-site"
module.LOANWORDS = {}

def export_review(frames):
    lines = [
        "# キミの記憶 -Reload-｜词卡审核稿", "",
        "整句中文来自 QQ 音乐翻译轨。当前拆词、读音、罗马音、词义和文法结构均为待审核草稿；助词只显示句中功能。", "",
    ]
    for frame in frames:
        caption = frame["caption"]
        lines.extend([
            f"## {frame['id']}　{frame['startMs'] / 1000:.3f}s", "",
            f"歌词：{caption.get('japanese', '')}", "",
            f"暂定中文：{caption.get('translationZh', '')}", "",
            f"分词罗马音：{caption.get('romaji', '')}", "", "待核词卡：", "",
        ])
        if not frame.get("grammarCards"):
            lines.append("- 无词卡（纯英文保持原位，不生成假名、罗马音或词卡）。")
        for card in frame.get("grammarCards", []):
            meaning = card.get("functionZh") or card.get("zhMeaning") or ""
            source = f"｜外来词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(f"- `{card['token']}`｜读音：{card['reading']}｜罗马音：{card['romaji']}｜暂定：{meaning}｜结构：{card['grammarStructureZh']}{source}")
        lines.append("")
    path = ROOT / "deliverables" / "review" / "kimi-no-kioku-reload-review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path

module.export_review = export_review
module.main()
