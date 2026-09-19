#!/usr/bin/env python3
"""Export the reviewable frames as a human-editable Markdown review.

`03-card-draft.md` requires `deliverables/review/<slug>-review.md`; `04-assisted-review.md`
requires the human edits in it to be imported with a field-level diff; `08-validation.md`
checks that they were. Those steps used to depend on one-off scripts kept outside the skill,
so a clone could not do them. This is the export half; `import_review_markdown.py` is the
import half.

The export also records a baseline snapshot and the file hash, so the importer can tell a
*human* edit from a later programmatic change and expose a conflict instead of guessing.

    python SKILL_ROOT/scripts/build_review_markdown.py PROJECT_ROOT
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewable(frame: dict) -> dict:
    """The fields a human is invited to edit, in a stable order."""
    cards = []
    for card in frame.get("grammarCards", []):
        cards.append({
            "token": card["token"], "reading": card.get("reading", ""), "romaji": card.get("romaji", ""),
            "meaning": card.get("zhMeaning") or card.get("functionZh") or "",
            "meaningField": "zhMeaning" if card.get("zhMeaning") else "functionZh",
            "grammar": card.get("grammarStructureZh", ""),
        })
    return {"japanese": frame["caption"]["japanese"],
            "translationZh": frame["caption"].get("translationZh", ""),
            "romaji": frame["caption"].get("romaji", ""),
            "cards": cards}


def render(document: dict, title: str) -> str:
    lines = [
        f"# {title}｜词卡逐行复核",
        "",
        "本文件是人工编辑入口：下面是每行的歌词、暂定中文与词卡。直接改本文件的内容，"
        "再用 `import_review_markdown.py` 按字段导入（只导入你改动过的字段，冲突会列出来）。",
        "",
    ]
    for frame in document["frames"]:
        data = reviewable(frame)
        lines.append(f"## {frame['id']}\u3000{frame['startMs'] / 1000:07.3f}")
        lines.append(f"歌词：{data['japanese']}")
        if data["translationZh"]:
            lines.append(f"暂定中文：{data['translationZh']}")
        lines.append("")
        if data["cards"]:
            lines.append("词卡：")
            for card in data["cards"]:
                lines.append(f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}")
                lines.append(f"  - 含义/功能：{card['meaning']}")
                lines.append(f"  - 词性：{card['grammar']}")
        else:
            lines.append("词卡：（无，纯英文行）")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--title", default=None)
    parser.add_argument("--stdout", action="store_true", help="Print instead of writing")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    document = load(project / "frames.json")
    manifest_path = project / "input-manifest.json"
    manifest = load(manifest_path)
    title = args.title or manifest.get("slug", root.name)
    text = render(document, title)
    if args.stdout:
        sys.stdout.write(text)
        return

    out = args.out or root / "deliverables" / "review" / f"{manifest.get('slug', root.name)}-review.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")

    baseline = {frame["id"]: reviewable(frame) for frame in document["frames"]}
    write(project / "review" / "review-markdown-baseline.json", {"schemaVersion": 1, "frames": baseline})
    manifest["reviewMarkdownSha256"] = sha(out)
    manifest["reviewMarkdownBaseline"] = f"{manifest.get('slug', root.name)}-review.md"
    write(manifest_path, manifest)
    print(json.dumps({"output": str(out.relative_to(root)).replace("\\", "/"),
                      "sha256": manifest["reviewMarkdownSha256"],
                      "baseline": "project/review/review-markdown-baseline.json",
                      "frames": len(baseline)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
