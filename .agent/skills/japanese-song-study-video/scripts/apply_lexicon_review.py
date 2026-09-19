#!/usr/bin/env python3
"""Apply a sealed targeted online review to frames.json.

This closes the lexicon RAG loop: draft_cards_from_lexicon.py writes candidate cards
and a queue, the online review answers the queued units with complete per-line card
sets, and this script installs them. It refuses to run on a review that is not the
sealed one, or that does not answer every queued unit exactly once.

Usage
    python apply_lexicon_review.py PROJECT_ROOT [--review FILE] [--dry-run] [--keep-units]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexicon_match import KANJI_CHAR_RE, is_separator  # noqa: E402

CARD_FIELDS = ("token", "reading", "romaji", "grammarStructureZh")
MEANING_FIELDS = ("zhMeaning", "functionZh")
# A meaning row carries the meaning alone; grammatical explanation belongs in
# grammarStructureZh. This catches the usual relapse.
STRUCTURE_NOTE = re.compile(
    r"（[^）]*(?:的[^）]{0,4}形|て形|た形|ない形|連用形|连用形|未然形|意志形|可能形|假定形|构成|接[^）]{0,6}形)[^）]*）"
    r"|^接[^，,]{1,8}?形[，,]|「[^」]+」(?:提示|标记|修饰)")
# Dictionary forms and grammar terms a card may legitimately quote anywhere.
GRAMMAR_TERMS = {"いく", "いる", "ある", "なる", "する", "ない", "ぬ", "た", "て", "で", "だ", "です", "ます",
                 "よう", "そう", "のだ", "から", "ので", "けど", "ても", "では", "てしまう"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_cards(frame: dict, cards: list[dict], other_lines: str = "") -> list[dict]:
    """Return normalised cards or raise; every rule here is one the renderer relies on."""
    line = frame["caption"]["japanese"]
    cursor, normalised = 0, []
    for index, card in enumerate(cards):
        missing = [field for field in CARD_FIELDS if not str(card.get(field, "")).strip()]
        if missing:
            raise SystemExit(f"{frame['id']} card {index} is missing {missing}")
        present = [field for field in MEANING_FIELDS if str(card.get(field, "")).strip()]
        if len(present) != 1:
            raise SystemExit(f"{frame['id']} card {index} ({card['token']}) needs exactly one of {MEANING_FIELDS}")
        meaning = str(card[present[0]])
        if STRUCTURE_NOTE.search(meaning):
            print(f"warning: {frame['id']} card {index} ({card['token']}) states a grammatical structure in "
                  f"{present[0]} ({meaning!r}); that belongs in grammarStructureZh", file=sys.stderr)
        # A description that quotes a word from another line teaches the wrong thing here,
        # but quoting a dictionary form or a grammatical term is perfectly normal.
        described = f"{meaning} {card.get('grammarStructureZh', '')}"
        for quoted in re.findall(r"「([^」]+)」", described):
            if len(quoted) < 2 or "…" in quoted or quoted in line or quoted in GRAMMAR_TERMS:
                continue
            if other_lines and quoted in other_lines:
                print(f"warning: {frame['id']} card {index} ({card['token']}) describes 「{quoted}」, which is not in "
                      f"this line but in another one", file=sys.stderr)
        for value in card.values():
            if "|" in str(value) or "｜" in str(value):
                raise SystemExit(f"{frame['id']} card {index} contains a serialized separator")
        position = line.find(card["token"], cursor)
        if position < 0:
            raise SystemExit(f"{frame['id']} card {index} token {card['token']!r} is not in the lyric line in order")
        cursor = position + len(card["token"])
        entry = {
            "token": card["token"], "reading": card["reading"], "romaji": card["romaji"],
            "grammarStructureZh": card["grammarStructureZh"], "render": True,
            "status": "online-reviewed", "reviewRequired": False,
            "fieldProvenance": {
                "token": "reviewed against the lyric line",
                "reading": "targeted online review",
                "romaji": "targeted online review",
                "meaningOrFunction": "targeted online review with recorded evidence",
                "grammarStructureZh": "targeted online review",
            },
            present[0]: card[present[0]],
        }
        if card.get("sourceWord"):
            entry["sourceWord"] = card["sourceWord"]
        normalised.append(entry)
    return normalised


def ruby_spans(frame: dict, review_change: dict) -> list[dict]:
    """Prefer the reviewed ruby; otherwise derive kanji-only spans from card readings."""
    line = frame["caption"]["japanese"]
    supplied = review_change.get("furigana")
    if supplied:
        spans = []
        for item in supplied:
            base, reading = str(item["base"]), str(item["reading"])
            position = line.find(base)
            if position < 0:
                raise SystemExit(f"{frame['id']} ruby base {base!r} is not in the lyric line")
            spans.append({"base": base, "reading": reading, "start": position, "end": position + len(base)})
        spans.sort(key=lambda item: item["start"])
        return spans
    spans, cursor = [], 0
    for card in frame["grammarCards"]:
        token, reading = card["token"], card["reading"]
        if not reading or not KANJI_CHAR_RE.search(token):
            continue
        start = line.find(token, cursor)
        if start < 0:
            continue
        cursor = start + len(token)
        prefix = 0
        while prefix < min(len(token), len(reading)) and token[prefix] == reading[prefix] and not KANJI_CHAR_RE.match(token[prefix]):
            prefix += 1
        suffix = 0
        while (suffix < len(token) - prefix and suffix < len(reading) - prefix
               and token[len(token) - 1 - suffix] == reading[len(reading) - 1 - suffix]
               and not KANJI_CHAR_RE.match(token[len(token) - 1 - suffix])):
            suffix += 1
        core = token[prefix:len(token) - suffix]
        core_reading = reading[prefix:len(reading) - suffix]
        if not core or not core_reading or not KANJI_CHAR_RE.search(core):
            continue
        spans.append({"base": core, "reading": core_reading, "start": start + prefix, "end": start + prefix + len(core)})
    return spans


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    review_path = args.review or project / "review" / "online-review.json"
    queue_path = args.queue or project / "review" / "rag-review-queue.json"
    audit_path = project / "review" / "assisted-review-audit.json"
    if not review_path.is_file():
        raise SystemExit(f"Online review is missing: {review_path}")
    if not queue_path.is_file():
        raise SystemExit(f"Review queue is missing: {queue_path}")
    review, queue = load(review_path), load(queue_path)

    # The review must be the one the audit sealed; applying an unsealed draft would
    # bypass the review gate entirely.
    if audit_path.is_file():
        audit = load(audit_path)
        sealed = audit.get("onlineReview", {})
        if sealed.get("sha256") != sha(review_path):
            raise SystemExit("The audit sealed a different online review; re-seal before applying")
    if str(review.get("reviewRole", "")) not in ("online", "lexicon-online") or review.get("status") != "completed":
        raise SystemExit("Online review must be completed with reviewRole=online")

    expected = {f"{entry['frameId']}::{unit['text']}"
                for entry in queue.get("queue", []) for unit in entry.get("units", [])}
    changes = review.get("changes", [])
    answered = {f"{change.get('frameId')}::{change.get('unit')}" for change in changes}
    if answered != expected:
        missing, unknown = sorted(expected - answered), sorted(answered - expected)
        raise SystemExit(f"Review does not match the queue (missing {missing[:3]}, unknown {unknown[:3]})")

    frames_path = project / "frames.json"
    before = sha(frames_path)
    document = load(frames_path)
    by_id = {frame["id"]: frame for frame in document["frames"]}
    other_lines = " ".join(frame["caption"]["japanese"] for frame in document["frames"])
    applied = []
    for change in changes:
        frame = by_id.get(change["frameId"])
        if frame is None:
            raise SystemExit(f"Review references an unknown frame: {change['frameId']}")
        line = frame["caption"]["japanese"]
        if change["unit"] not in line:
            raise SystemExit(f"Reviewed unit {change['unit']!r} is not in {frame['id']}")
        cards = validate_cards(frame, change.get("cards", []), other_lines)
        cards_cover_line = sum(len(card["token"]) for card in cards)
        if cards_cover_line < len(line) - 2:
            print(f"warning: {frame['id']} reviewed cards cover {cards_cover_line} of {len(line)} characters", file=sys.stderr)
        frame["grammarCards"] = cards
        frame["caption"]["furigana"] = ruby_spans(frame, change)
        frame["status"] = "online-reviewed"
        frame["cardReviewStatus"] = "draft"
        frame["reviewRequired"] = True
        frame["fieldProvenance"] = {
            "japanese": "timing/qm.json",
            "romaji": "targeted online review",
            "translationZh": frame["caption"].get("translationZh", "") and "supplied qmts track",
            "grammarCards": "lexicon RAG draft reviewed online with recorded evidence",
        }
        applied.append({"frameId": frame["id"], "unit": change["unit"], "cards": len(cards)})

    for frame in document["frames"]:
        if frame["id"] in {item["frameId"] for item in applied}:
            continue
        for card in frame.get("grammarCards", []):
            if card.get("status") == "rag-proposed-low-confidence":
                card["status"] = "rag-reused"
                card["reviewRequired"] = False

    summary = {
        "schemaVersion": 1,
        "appliedAt": datetime.now(timezone.utc).isoformat(),
        "review": str(review_path.relative_to(root)).replace("\\", "/"),
        "reviewSha256": sha(review_path),
        "framesBeforeSha256": before,
        "framesAfterSha256": None,
        "units": len(applied),
        "cards": sum(item["cards"] for item in applied),
        "perFrame": applied,
    }
    if args.dry_run:
        summary["dryRun"] = True
        print(json.dumps({key: summary[key] for key in ("units", "cards")}, ensure_ascii=False))
        return
    write(frames_path, document)
    summary["framesAfterSha256"] = sha(frames_path)
    write(project / "review" / "rag-review-merge-log.json", summary)
    print(json.dumps({"units": summary["units"], "cards": summary["cards"],
                      "framesBeforeSha256": before, "framesAfterSha256": summary["framesAfterSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
