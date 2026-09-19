#!/usr/bin/env python3
"""Import human edits from the review Markdown with a field-level three-way diff.

The baseline snapshot written by `build_review_markdown.py` describes the frames as the
human last saw them. Comparing it with the edited Markdown gives the human's edits;
comparing it with the current `frames.json` gives later programmatic changes. A field only
one side touched is imported or preserved silently; a field both sides changed differently
is reported as a conflict and never guessed by file modification time - the rule
`04-assisted-review.md` states.

    python SKILL_ROOT/scripts/import_review_markdown.py PROJECT_ROOT [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CARD_LINE = re.compile(r"^-\s+`([^`]+)`｜([^｜]*)｜(.*)$")
FRAME_HEADING = re.compile(r"^##\s+(\S+?)[\u3000\s]+(\d+(?:\.\d+)?)\s*$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(markdown: str) -> dict:
    """Read the exported shape back: per frame, its line text, translation and card fields."""
    frames: dict[str, dict] = {}
    current = None
    pending = None
    for raw in markdown.splitlines():
        line = raw.rstrip()
        heading = FRAME_HEADING.match(line)
        if heading:
            current = heading.group(1)
            frames[current] = {"cards": []}
            pending = None
            continue
        if current is None:
            continue
        if line.startswith("歌词："):
            frames[current]["japanese"] = line[3:].strip()
        elif line.startswith("暂定中文："):
            frames[current]["translationZh"] = line[5:].strip()
        else:
            card = CARD_LINE.match(line)
            if card:
                pending = {"token": card.group(1), "reading": card.group(2), "romaji": card.group(3).strip(),
                           "meaning": "", "meaningField": None, "grammar": ""}
                frames[current]["cards"].append(pending)
            elif pending is not None and line.strip().startswith("- 含义/功能："):
                pending["meaning"] = line.split("：", 1)[1].strip()
                pending["meaningField"] = "zhMeaning"
            elif pending is not None and line.strip().startswith("- 词性："):
                pending["grammar"] = line.split("：", 1)[1].strip()
    return frames


def comparable(data: dict) -> dict:
    """The fields the importer can compare, normalised for equality checks."""
    return {"japanese": data.get("japanese", ""), "translationZh": data.get("translationZh", ""),
            "cards": [{"token": card["token"], "reading": card.get("reading", ""), "romaji": card.get("romaji", ""),
                       "meaning": card.get("meaning", ""), "grammar": card.get("grammar", "")}
                      for card in data.get("cards", [])]}


def current_view(frame: dict) -> dict:
    return {"japanese": frame["caption"]["japanese"],
            "translationZh": frame["caption"].get("translationZh", ""),
            "cards": [{"token": card["token"], "reading": card.get("reading", ""), "romaji": card.get("romaji", ""),
                       "meaning": card.get("zhMeaning") or card.get("functionZh") or "",
                       "grammar": card.get("grammarStructureZh", "")}
                      for card in frame.get("grammarCards", [])]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    manifest = load(project / "input-manifest.json")
    slug = manifest.get("slug", root.name)
    markdown_path = args.markdown or root / "deliverables" / "review" / f"{slug}-review.md"
    baseline_path = args.baseline or project / "review" / "review-markdown-baseline.json"
    if not markdown_path.is_file():
        raise SystemExit(f"Review Markdown is missing: {markdown_path}")
    if not baseline_path.is_file():
        raise SystemExit(f"Baseline is missing: {baseline_path}. Run build_review_markdown.py first.")

    baseline = load(baseline_path)["frames"]
    edited = parse(markdown_path.read_text(encoding="utf-8"))
    document = load(project / "frames.json")
    by_id = {frame["id"]: frame for frame in document["frames"]}

    imported, conflicts, unknown = [], [], []
    for frame_id, before in baseline.items():
        frame = by_id.get(frame_id)
        if frame is None or frame_id not in edited:
            unknown.append(frame_id)
            continue
        now, human = current_view(frame), comparable(edited[frame_id])
        base = comparable(before)
        for field in ("translationZh",):
            if human[field] != base[field]:
                if now[field] == base[field]:
                    imported.append({"frameId": frame_id, "field": field, "old": now[field], "new": human[field]})
                    frame["caption"]["translationZh"] = human[field]
                elif now[field] != human[field]:
                    conflicts.append({"frameId": frame_id, "field": field, "baseline": base[field],
                                      "markdown": human[field], "frames": now[field]})
        base_cards, now_cards = base["cards"], now["cards"]
        if [card["token"] for card in human["cards"]] != [card["token"] for card in base_cards]:
            conflicts.append({"frameId": frame_id, "field": "cards", "reason": "token structure changed in the Markdown",
                              "baseline": [card["token"] for card in base_cards],
                              "markdown": [card["token"] for card in human["cards"]]})
            continue
        if len(now_cards) == len(base_cards):
            for index, (human_card, base_card, now_card) in enumerate(zip(human["cards"], base_cards, now_cards)):
                for field, key in (("meaning", None), ("reading", "reading"), ("romaji", "romaji"), ("grammar", "grammarStructureZh")):
                    if human_card[field] == base_card[field]:
                        continue
                    if now_card[field] == base_card[field]:
                        target = frame["grammarCards"][index]
                        if field == "meaning":
                            meaning_field = "zhMeaning" if target.get("zhMeaning") else "functionZh"
                            imported.append({"frameId": frame_id, "field": f"cards[{index}].{meaning_field}",
                                             "old": now_card[field], "new": human_card[field]})
                            target[meaning_field] = human_card[field]
                            target.pop("functionZh" if meaning_field == "zhMeaning" else "zhMeaning", None)
                        else:
                            imported.append({"frameId": frame_id, "field": f"cards[{index}].{key}",
                                             "old": now_card[field], "new": human_card[field]})
                            target[key] = human_card[field]
                    elif now_card[field] != human_card[field]:
                        conflicts.append({"frameId": frame_id, "field": f"cards[{index}].{field}",
                                          "baseline": base_card[field], "markdown": human_card[field],
                                          "frames": now_card[field]})
        else:
            conflicts.append({"frameId": frame_id, "field": "cards",
                              "reason": "card count differs between the baseline and the current frames",
                              "baseline": len(base_cards), "frames": len(now_cards)})

    report = {"schemaVersion": 1, "markdown": str(markdown_path.relative_to(root)).replace("\\", "/"),
              "markdownSha256": sha(markdown_path), "imported": imported, "conflicts": conflicts,
              "unknownFrames": unknown,
              "result": "conflicts" if conflicts else ("imported" if imported else "no-changes")}
    report_path = args.report or project / "review" / "review-markdown-import.json"
    write(report_path, report)
    if args.apply and imported:
        write(project / "frames.json", document)
        manifest["reviewMarkdownSha256"] = report["markdownSha256"]
        write(project / "input-manifest.json", manifest)
    print(json.dumps({**report, "applied": bool(args.apply and imported),
                      "report": str(report_path.relative_to(root)).replace("\\", "/")},
                     ensure_ascii=False, indent=2))
    raise SystemExit(2 if conflicts else 0)


if __name__ == "__main__":
    main()
