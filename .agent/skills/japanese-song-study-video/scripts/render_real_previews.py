#!/usr/bin/env python3
"""Render the two real-content preview sets every project needs.

``setup`` samples prove the layer structure and the foreground geometry:
prelude, each countdown value, first sung unit, a line with both neighbours, a
mid-video gap, a late line and the tail.

``draft`` samples prove the card layout with the hardest real content: the longest
lyric, the longest card meaning, the row with the most cards, a mixed
Japanese/English row, a pure English row and the row with the most ruby.

Both go to ``deliverables/review/`` (for the user) with the machine-readable
report in ``project/qa/``. Real renderer, real background, real spectrum - no
synthesised placeholder content.

Usage
    python render_real_previews.py PROJECT_ROOT [--run-id ID] [--timeline FILE] [--spectrum FILE]
        [--sets setup,draft] [--out-dir DIR] [--prefix TEXT]
"""
from __future__ import annotations

import argparse
import json
import sys
from shutil import copyfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_render import ProjectStill, load, load_renderer  # noqa: E402


def has_ascii_word(frame: dict) -> bool:
    return any(ord(character) < 0x3000 and character.isalpha() for character in frame["caption"]["japanese"])


def is_pure_english(frame: dict) -> bool:
    return not frame.get("grammarCards") and all(
        ord(character) < 0x3000 for character in frame["caption"]["japanese"] if character.isalpha()
    )


def setup_samples(still: ProjectStill) -> list[tuple[str, int | None, str | None]]:
    """(label, outputMs, frameId) with outputMs None meaning 'first active state of frameId'."""
    timeline = still.require_timeline()
    segments = timeline["segments"]
    countdown = {item["value"]: (item["startMs"] + item["endMs"]) // 2 for item in timeline.get("countdown", {}).get("segments", [])}
    onset = timeline.get("countdown", {}).get("onsetMs")
    ordered = [frame for frame in still.frames if frame["id"] in {segment.get("frameId") for segment in segments}]
    samples: list[tuple[str, int | None, str | None]] = [("prelude", 0, None)]
    for value in (3, 2, 1):
        if value in countdown:
            samples.append((f"countdown-{value}", countdown[value], None))
    if onset is not None:
        samples.append(("first-sung-unit", onset + 50, None))
    with_neighbours = next(
        (frame for index, frame in enumerate(ordered) if 0 < index < len(ordered) - 1 and frame.get("grammarCards")), None
    )
    if with_neighbours is not None:
        samples.append(("line-with-neighbours", None, with_neighbours["id"]))
    blank = next((segment for segment in segments if segment["kind"] == "blank" and segment["startMs"] > 0), None)
    if blank is not None:
        samples.append(("interlude-blank", blank["startMs"] + min(100, (blank["endMs"] - blank["startMs"]) // 2), None))
    if len(ordered) > 3:
        samples.append(("late-line", None, ordered[-2]["id"]))
    samples.append(("final-line", None, ordered[-1]["id"]) if ordered else ("final-line", 0, None))
    return samples


def draft_samples(still: ProjectStill) -> list[tuple[str, str]]:
    frames = [frame for frame in still.frames if frame.get("grammarCards")]
    if not frames:
        return []
    def meaning_of(frame: dict) -> str:
        return max((card.get("zhMeaning") or card.get("functionZh") or "" for card in frame["grammarCards"]), key=len, default="")
    japanese_only = [frame for frame in frames if not has_ascii_word(frame)] or frames
    samples = [
        ("longest-lyric", max(japanese_only, key=lambda frame: len(frame["caption"]["japanese"]))["id"]),
        ("longest-meaning", max(frames, key=lambda frame: len(meaning_of(frame)))["id"]),
        ("maximum-cards", max(frames, key=lambda frame: len(frame["grammarCards"]))["id"]),
    ]
    mixed = next((frame for frame in frames if has_ascii_word(frame)), None)
    if mixed is not None:
        samples.append(("mixed-japanese-english", mixed["id"]))
    english = next((frame for frame in still.frames if is_pure_english(frame)), None)
    if english is not None:
        samples.append(("pure-english", english["id"]))
    chosen = {frame_id for _, frame_id in samples}
    remainder = [frame for frame in frames if frame["id"] not in chosen] or frames
    samples.append(("kanji-ruby", max(remainder, key=lambda frame: (len(frame["caption"].get("furigana", [])),
                                                                   len(frame["caption"]["japanese"])))["id"]))
    return samples


def romaji_collision_report(still: ProjectStill, renderer) -> dict:
    """Measure whether neighbouring tokens' centred romaji overlap.

    The template anchors each token's romaji under that token, so a narrow token beside a
    wider romaji lets the later-drawn string cover the earlier one (私/が rendered as
    "watashi g watashi o"). Measuring it here catches the problem before a long render; the
    remedy is a content decision (merge the pair into one chunk).
    """
    from PIL import Image, ImageDraw

    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    threshold = 8  # below this the glyphs do not actually touch
    collisions, worst = [], 0
    for frame in still.frames:
        cards = frame.get("grammarCards", [])
        for index in range(len(cards) - 1):
            sizes = []
            for card in (cards[index], cards[index + 1]):
                token = draw.textbbox((0, 0), card["token"], font=renderer.font(70))[2]
                romaji = draw.textbbox((0, 0), card.get("romaji", ""), font=renderer.font(34))[2] if card.get("romaji") else 0
                sizes.append((token, romaji))
            (left_token, left_romaji), (right_token, right_romaji) = sizes
            overlap = (left_romaji + right_romaji) - (left_token + right_token)
            worst = max(worst, overlap)
            if overlap > threshold:
                collisions.append({
                    "frameId": frame["id"], "overlapPx": overlap,
                    "pair": f"{cards[index]['token']} || {cards[index + 1]['token']}",
                    "hint": "merge the pair into one chunk so each romaji stays inside its own column",
                })
    return {"visibleOverlapPx": threshold, "worstOverlapPx": worst,
            "collisionCount": len(collisions), "collisions": collisions}


def draft_fit_report(still: ProjectStill, renderer) -> dict:
    """Measure every card against the fixed one-row card box.

    The renderer shrinks the token and grammar fields to a minimum font and fails on
    overflow, so this predicts exactly which cards would abort a render instead of
    discovering it 200 states in.
    """
    from PIL import Image, ImageDraw
    from render_video import wrap

    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    findings, problems = [], []
    frames_with_cards = [frame for frame in still.frames if frame.get("grammarCards")]
    for frame in frames_with_cards:
        cards = frame["grammarCards"]
        gap, total = renderer.px(12), renderer.px(1730, "x")
        card_width = (total - gap * (len(cards) - 1)) // len(cards)
        inner = card_width - renderer.px(28)
        for index, card in enumerate(cards):
            present = [field for field in ("zhMeaning", "functionZh") if str(card.get(field, "")).strip()]
            if len(present) != 1:
                problems.append(f"{frame['id']} card {index} ({card['token']}) must carry exactly one of "
                                f"zhMeaning/functionZh, found {present}")
            meaning = card.get("zhMeaning") or card.get("functionZh") or ""
            lines = wrap(draw, meaning, renderer.font(26), inner)
            token_ok = draw.textbbox((0, 0), card["token"], font=renderer.font(16))[2] <= inner
            grammar = card.get("grammarStructureZh") or ""
            # The grammar row may occupy two lines (user rule); it only fails if it needs more.
            grammar_lines = wrap(draw, grammar, renderer.font(22), inner)
            grammar_ok = len(grammar_lines) <= 2
            findings.append({
                "frameId": frame["id"], "index": index, "cards": len(cards), "innerWidthPx": inner,
                "tokenFitsAtMinimum": token_ok, "grammarFitsTwoLines": grammar_ok,
                "grammarLines": len(grammar_lines),
                "meaningLines": len(lines), "meaningFitsTwoLines": len(lines) <= 2,
            })
            if not (token_ok and grammar_ok and len(lines) <= 2):
                problems.append(f"{frame['id']} card {index} ({card['token']}): "
                                f"token={token_ok} grammar={grammar_ok} grammarLines={len(grammar_lines)} "
                                f"meaningLines={len(lines)}")
    collisions = romaji_collision_report(still, renderer)
    if collisions["collisionCount"]:
        problems.extend(f"{item['frameId']} romaji overlap {item['overlapPx']}px: {item['pair']}"
                        for item in collisions["collisions"][:10])
    return {
        "schemaVersion": 1,
        "type": "draft-layout-report",
        "result": "passed" if not problems else "failed",
        "framesChecked": len(frames_with_cards),
        "cardsChecked": len(findings),
        "tightestInnerWidthPx": min((item["innerWidthPx"] for item in findings), default=None),
        "maxMeaningLines": max((item["meaningLines"] for item in findings), default=0),
        "maxGrammarLines": max((item["grammarLines"] for item in findings), default=0),
        "romaji": collisions,
        "problems": problems,
        "findings": findings,
        "note": "Cards occupy one horizontal row; the token stays on one line, the meaning/function wraps to at most "
                "two lines and the grammar structure may also use two lines.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--spectrum", type=Path)
    parser.add_argument("--sets", default="setup,draft")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--prefix")
    args = parser.parse_args()

    root = args.project_root.resolve()
    manifest = load(root / "project" / "input-manifest.json")
    still = ProjectStill(root, timeline_path=args.timeline, spectrum_path=args.spectrum, run_id=args.run_id)
    still.require_timeline()
    renderer = load_renderer(root)
    slug = manifest.get("slug", root.name)
    prefix = args.prefix or slug
    output_dir = args.out_dir or root / "deliverables" / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    wanted = {value.strip() for value in args.sets.split(",") if value.strip()}

    report: dict = {"schemaVersion": 1, "type": "real-content-previews", "sets": {}, "result": "pending-visual-review"}
    if "setup" in wanted:
        samples = []
        for label, timestamp_ms, frame_id in setup_samples(still):
            output = output_dir / f"{prefix}--setup-preview--{label}.png"
            if frame_id:
                info = still.still(renderer, frame_id, output)
            else:
                # Time-based sample: the state at that moment may be a gap or the
                # cover, where no single frame is on screen.
                info = still.still(renderer, None, output, seconds=timestamp_ms / 1000)
            samples.append({"label": label, **info})
        first = next((sample for sample in samples if sample["frameId"]), None)
        if first:
            copyfile(root / first["relativePath"], root / "project" / "qa" / "structure-preview-16x9.png")
        report["sets"]["setup"] = {"samples": samples, "report": "project/qa/structure-report.json"}
        (root / "project" / "qa" / "structure-report.json").write_text(json.dumps({
            "schemaVersion": 1, "type": "setup-structure-preview", "result": "pending-visual-review",
            "layers": ["background", "foreground", "floatingOverlay"],
            "samples": [{"label": sample["label"], "frameId": sample["frameId"], "outputSeconds": sample["outputSeconds"],
                         "path": sample["relativePath"]} for sample in samples],
            "coverage": {"prelude": "first study frame unhighlighted",
                         "countdown": "every value 3/2/1 before the first sung unit",
                         "neighbours": "static previous/next lyric, no highlight",
                         "gaps": "blank foreground between lines",
                         "tail": "final line hides after the protection window"},
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if "draft" in wanted:
        # Measure first: a field that cannot fit even at the minimum font aborts the
        # renderer, so report the exact fields instead of crashing mid-render.
        fit = draft_fit_report(still, renderer)
        (root / "project" / "qa" / "draft-layout-report.json").write_text(
            json.dumps(fit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        if fit["result"] != "passed":
            report["sets"]["draft"] = {"samples": [], "report": "project/qa/draft-layout-report.json", "result": "failed"}
            report_path = root / "project" / "qa" / "real-previews-report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(json.dumps({"result": "failed", "report": "project/qa/draft-layout-report.json",
                              "problems": fit["problems"][:10], "hint": "Shorten the named field; the card box is fixed."},
                             ensure_ascii=False, indent=2))
            raise SystemExit(1)
        samples = []
        for label, frame_id in draft_samples(still):
            output = output_dir / f"{prefix}--draft-preview--{label}.png"
            samples.append({"label": label, **still.still(renderer, frame_id, output)})
        report["sets"]["draft"] = {"samples": samples, "report": "project/qa/draft-layout-report.json", "result": fit["result"]}
        fit["samples"] = [{"label": sample["label"], "frameId": sample["frameId"],
                           "outputSeconds": sample["outputSeconds"], "path": sample["relativePath"]} for sample in samples]
        (root / "project" / "qa" / "draft-layout-report.json").write_text(
            json.dumps(fit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    report_path = root / "project" / "qa" / "real-previews-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(report_path.relative_to(root)).replace("\\", "/"),
                      "sets": {key: len(value["samples"]) for key, value in report["sets"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
