#!/usr/bin/env python3
"""Refresh derived review artifacts after an accepted merge.

Run after project/render/apply_review_merge.py. It never touches frames.json;
it rebuilds everything derived from it:

  * deliverables/review/<slug>-review.md   (export of the confirmed frames)
  * project/particle-functions.json        (rebuilt from the cards in use)
  * project/review/draft-manifest.json     (hashes / counts)

If the review Markdown on disk does not match the hash recorded in the draft
manifest, the file was hand-edited: the script stops so those edits can be
imported deliberately instead of being overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
parser = argparse.ArgumentParser()
parser.add_argument("--project-root", type=Path, required=True, help="Project root, e.g. projects/<slug>")
parser.add_argument("--slug", help="Defaults to input-manifest.json slug")
args = parser.parse_args()
ROOT = args.project_root.resolve()
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
REVIEW = ROOT / "deliverables" / "review" / f"{(args.slug or json.loads((ROOT / 'project' / 'input-manifest.json').read_text(encoding='utf-8')).get('slug', ROOT.name))}-review.md"
MANIFEST = PROJECT / "review" / "draft-manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


frames = json.loads(FRAMES.read_text(encoding="utf-8"))
manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
if REVIEW.is_file() and manifest.get("reviewMarkdownSha256") not in (None, sha(REVIEW)):
    raise SystemExit(
        "deliverables/review/eternel-review.md was hand-edited after the draft export; "
        "import those edits deliberately instead of regenerating over them."
    )

confirmed = all(frame.get("cardReviewStatus") == "human-confirmed" for frame in frames["frames"] if frame["grammarCards"])
lines = [
    "# エテルネル｜" + ("已确认词卡" if confirmed else "待审核词卡"),
    "",
    "整句中文原样取自你提供的 QQ 音乐翻译文件（qmts 轨）。"
    + ("以下分词、读音、罗马音、词义与结构已按你确认的整合方案定稿。" if confirmed else "以下分词、读音、罗马音、词义与结构均为待审核草稿，尚未人工确认。")
    + "助词只展示句中功能，不展示字典义。纯英文行不生成词卡、假名与罗马音。",
    "",
]
particles: dict[str, list[str]] = {}
card_count = 0
for frame in frames["frames"]:
    lines.append(f"## {frame['id']}　{frame['caption']['japanese']}")
    lines.append("")
    lines.append(f"暂定中文：{frame['caption']['translationZh']}")
    lines.append("")
    cards = frame["grammarCards"]
    if not cards:
        lines.append("词卡：无（纯英文行保留原位置与高亮，不生成词卡、假名与罗马音）")
    else:
        ruby = "；".join(f"{item['base']}（{item['reading']}）" for item in frame["caption"]["furigana"]) or "无"
        lines.append(f"假名注音：{ruby}")
        lines.append("")
        lines.append("词卡：")
        lines.append("")
        for card in cards:
            card_count += 1
            meaning = card.get("zhMeaning") or card.get("functionZh")
            lines.append(f"- {card['token']}（{card['reading']} / {card['romaji']}）——{meaning}；{card['grammarStructureZh']}")
            if card.get("functionZh"):
                bucket = particles.setdefault(card["token"], [])
                if card["functionZh"] not in bucket:
                    bucket.append(card["functionZh"])
    if frame.get("reviewNote"):
        lines.append("")
        lines.append(f"备注：{frame['reviewNote']}")
    lines.append("")
write(REVIEW, "\n".join(lines) + "\n")

write(PROJECT / "particle-functions.json", json.dumps({
    "schemaVersion": 2,
    "status": "confirmed" if confirmed else "draft",
    "note": "Rebuilt from the cards actually in use; every functionZh in frames.json appears here.",
    "functions": {token: values for token, values in sorted(particles.items())},
}, ensure_ascii=False, indent=2) + "\n")

manifest.update({
    "schemaVersion": 1,
    "frameSha256": sha(FRAMES),
    "frameCount": len(frames["frames"]),
    "cardCount": card_count,
    "englishFrames": [frame["id"] for frame in frames["frames"] if not frame["grammarCards"]],
    "reviewMarkdown": "deliverables/review/eternel-review.md",
    "reviewMarkdownSha256": sha(REVIEW),
    "particleFunctions": "project/particle-functions.json",
    "contentApproved": confirmed,
})
write(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

print(json.dumps({
    "frameSha256": manifest["frameSha256"],
    "cards": card_count,
    "confirmed": confirmed,
    "particleTokens": len(particles),
}, ensure_ascii=False))
