#!/usr/bin/env python3
"""Build a per-line review gallery: one real render still plus the card table.

Reviewing cards line by line is a fixed need in every project, so it lives in the
skill instead of being rewritten per project. Each lyric row gets a finished-video
still (background + foreground + floating spectrum) taken while that row is
actually on screen, beside its card list in reading order. When a change set is
supplied, the fields it would alter are marked inline as old -> new.

Usage
    python build_review_gallery.py PROJECT_ROOT [--run-id ID] [--timeline FILE] [--spectrum FILE]
        [--changes FILE] [--out-dir DIR] [--title TEXT] [--still-width N] [--no-inline-images]

By default every still is embedded in the HTML as a data URI, so the page renders
even when a viewer serves the file on its own (a GUI preview or a chat attachment)
instead of from its directory.
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_render import ProjectStill, load, load_renderer  # noqa: E402


def inline_data_uri(path: Path, quality: int = 85) -> str:
    """JPEG data URI small enough to embed, large enough to judge a card row."""
    from PIL import Image

    with Image.open(path) as image:
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

STYLES = """
body{font-family:'Microsoft YaHei',sans-serif;background:#14161a;color:#e8e8e8;margin:0;padding:24px 32px 96px}
h1{font-size:22px;margin:0 0 6px}p.lead{color:#b9c0c8;font-size:13px;line-height:1.7;margin:0 0 22px}
.line{border:1px solid #2b3038;border-radius:10px;margin:0 0 22px;overflow:hidden;background:#191c21}
.line header{display:flex;gap:12px;align-items:baseline;padding:12px 16px;background:#1f242b}
.line header .id{font-family:Consolas,monospace;color:#9ad;font-size:13px}
.line header .jp{font-size:17px;font-weight:700}
.line header .t{color:#8b93a0;font-size:12px;margin-left:auto}
.line .body{display:flex;gap:16px;padding:14px 16px;align-items:flex-start}
.line img{width:520px;border-radius:6px;border:1px solid #2b3038}
.cards{flex:1;min-width:0}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid #262b33;vertical-align:top}
th{color:#8b93a0;font-weight:400;font-size:12px}
.tk{font-weight:700;font-size:15px}.rd{color:#9ad;font-size:12px}.rm{color:#8b93a0;font-size:12px}
.chg{background:#2a2312}.chg .arrow{color:#f0c419;font-weight:700}
.new{color:#ffd75e;font-weight:700}.old{color:#7d8590;text-decoration:line-through}
.tag{display:inline-block;background:#2b3038;color:#b9c0c8;font-size:11px;border-radius:4px;padding:1px 6px;margin-left:6px}
.zh{margin:2px 0 10px;color:#dfe4ea;font-size:14px}
.ruby{color:#9ad;font-size:12px;margin:2px 0 10px}
.en{color:#b9c0c8;font-size:13px}
.note{color:#f0c419;font-size:12px;margin-top:6px}
"""


def load_changes(path: Path | None) -> dict[str, list[dict]]:
    """Index a change set by frame so a card field can be shown as old -> new."""
    if path is None:
        return {}
    document = load(path)
    indexed: dict[str, list[dict]] = {}
    for operation in document.get("operations", []):
        frame = operation.get("frameId")
        if not frame:
            continue
        entry = {"field": operation.get("field", ""), "old": operation.get("old", ""), "new": operation.get("new", "")}
        if operation.get("op") == "mergeCards":
            card = operation.get("newCard", {})
            entry = {"field": "grammarCards", "old": " + ".join(operation.get("expectedTokens", [])),
                     "new": f"{card.get('token', '')}（{card.get('reading', '')} / {card.get('romaji', '')}；{card.get('zhMeaning') or card.get('functionZh', '')}；{card.get('grammarStructureZh', '')}）"}
        indexed.setdefault(frame, []).append(entry)
    return indexed


def change_for(changes: dict[str, list[dict]], frame_id: str, field_path: str) -> dict | None:
    for entry in changes.get(frame_id, []):
        if entry["field"] == field_path:
            return entry
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--spectrum", type=Path)
    parser.add_argument("--changes", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--still-width", type=int, default=960, help="Stored still width (scaled from the canvas)")
    parser.add_argument("--no-inline-images", action="store_true",
                        help="Reference the stills by relative path instead of embedding them")
    parser.add_argument("--inline-quality", type=int, default=85)
    args = parser.parse_args()

    root = args.project_root.resolve()
    manifest = load(root / "project" / "input-manifest.json")
    still = ProjectStill(root, timeline_path=args.timeline, spectrum_path=args.spectrum, run_id=args.run_id)
    timeline = still.require_timeline()
    renderer = load_renderer(root)
    changes = load_changes(args.changes)
    output_dir = args.out_dir or root / "deliverables" / "review" / "gallery"
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = manifest.get("slug", root.name)

    rows = []
    for frame in still.frames:
        image_path = output_dir / f"{frame['id']}.png"
        info = still.still(renderer, frame["id"], image_path)
        from PIL import Image
        with Image.open(image_path) as image:
            image.resize((args.still_width, round(args.still_width * image.height / image.width))).save(image_path)
        cards = []
        for index, card in enumerate(frame.get("grammarCards", [])):
            meaning_key = "zhMeaning" if card.get("zhMeaning") else "functionZh"
            cards.append({
                "index": index, "token": card["token"], "reading": card.get("reading", ""), "romaji": card.get("romaji", ""),
                "meaning": card.get(meaning_key, ""), "meaningKey": meaning_key, "grammar": card.get("grammarStructureZh", ""),
                "meaningChange": change_for(changes, frame["id"], f"grammarCards[{index}].{meaning_key}"),
                "grammarChange": change_for(changes, frame["id"], f"grammarCards[{index}].grammarStructureZh"),
                "status": card.get("status", ""),
            })
        rows.append({
            "id": frame["id"], "startMs": frame["startMs"], "seconds": info["outputSeconds"],
            "japanese": frame["caption"]["japanese"], "translationZh": frame["caption"].get("translationZh", ""),
            "furigana": frame["caption"].get("furigana", []), "cards": cards,
            "still": (inline_data_uri(image_path, args.inline_quality) if not args.no_inline_images
                      else f"{output_dir.name}/{frame['id']}.png"),
            "stillRelativePath": info["relativePath"],
            "english": not frame.get("grammarCards"),
            "merge": next((entry for entry in changes.get(frame["id"], []) if entry["field"] == "grammarCards"), None),
        })

    title = args.title or f"{slug}｜词卡逐行预览"
    parts = [
        "<!doctype html>", '<html lang="zh-CN"><head><meta charset="utf-8">',
        f"<title>{html.escape(title)}</title>", f"<style>{STYLES}</style></head><body>",
        f"<h1>{html.escape(title)}</h1>",
        '<p class="lead">每行一张真实渲染静帧（背景 + 前景 + 频谱的真实合成，取该行实际在屏的一帧）。'
        + ("图片已内嵌在本页中，因此单独打开本文件也能看到图。" if not args.no_inline_images
           else f"图片位于 <code>{html.escape(output_dir.name)}/</code> 子目录，请连同该目录一起打开。")
        + "黄色底纹行 = 提案将修改的字段（左：现值，右：提案值）。</p>",
    ]
    for row in rows:
        parts.append('<section class="line">')
        parts.append(f'<header><span class="id">{row["id"]}</span><span class="jp">{html.escape(row["japanese"])}</span>'
                     f'<span class="t">{row["startMs"] / 1000:.2f}s</span></header>')
        parts.append('<div class="body">')
        parts.append(f'<img src="{row["still"]}" alt="{row["id"]}">')
        parts.append('<div class="cards">')
        if row["english"]:
            parts.append('<p class="en">纯英文行：保留英文位置与逐字高亮，不生成词卡、假名与罗马音。</p>')
        else:
            ruby = "、".join(f'{item["base"]}（{item["reading"]}）' for item in row["furigana"]) or "无"
            parts.append(f'<p class="ruby">假名注音：{html.escape(ruby)}</p>')
        parts.append(f'<p class="zh">整句中文：{html.escape(row["translationZh"])}</p>')
        if row["merge"]:
            parts.append(f'<p class="note">提案：合并 {html.escape(row["merge"]["old"])} → <b>{html.escape(row["merge"]["new"])}</b></p>')
        if row["cards"]:
            parts.append("<table><tr><th>#</th><th>词块</th><th>读音 / 罗马音</th><th>释义 / 功能</th><th>语法结构</th></tr>")
            for card in row["cards"]:
                meaning_cell = html.escape(card["meaning"])
                if card["meaningChange"]:
                    meaning_cell = (f'<span class="old">{html.escape(card["meaningChange"]["old"])}</span> '
                                    f'<span class="arrow">→</span> <span class="new">{html.escape(card["meaningChange"]["new"])}</span>')
                grammar_cell = html.escape(card["grammar"])
                if card["grammarChange"]:
                    grammar_cell = (f'<span class="old">{html.escape(card["grammarChange"]["old"])}</span> '
                                    f'<span class="arrow">→</span> <span class="new">{html.escape(card["grammarChange"]["new"])}</span>')
                css = ' class="chg"' if (card["meaningChange"] or card["grammarChange"]) else ""
                label = "功能" if card["meaningKey"] == "functionZh" else "释义"
                parts.append(
                    f'<tr{css}><td>{card["index"] + 1}</td><td class="tk">{html.escape(card["token"])}</td>'
                    f'<td><span class="rd">{html.escape(card["reading"])}</span><br><span class="rm">{html.escape(card["romaji"])}</span></td>'
                    f'<td>{meaning_cell}<span class="tag">{label}</span></td><td>{grammar_cell}</td></tr>'
                )
            parts.append("</table>")
        parts.append("</div></div></section>")
    parts.append("</body></html>")

    index_path = output_dir.parent / f"{slug}-词卡逐行预览.html"
    index_path.write_text("\n".join(parts) + "\n", encoding="utf-8", newline="\n")
    report = {
        "schemaVersion": 1,
        "type": "review-gallery",
        "index": str(index_path.relative_to(root)).replace("\\", "/"),
        "stills": len(rows),
        "stillDir": str(output_dir.relative_to(root)).replace("\\", "/"),
        "timeline": str(still.timeline_path.relative_to(root)).replace("\\", "/") if still.timeline_path else None,
        "spectrum": str(still.spectrum.relative_to(root)).replace("\\", "/") if still.spectrum else None,
        "changesMarked": sum(len(value) for value in changes.values()),
        "timelineSummary": timeline.get("summary", {}),
    }
    (root / "project" / "qa" / "review-gallery-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
