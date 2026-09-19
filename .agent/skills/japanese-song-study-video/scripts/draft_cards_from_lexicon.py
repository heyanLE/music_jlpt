#!/usr/bin/env python3
"""Draft a project's cards from the workspace lexicon (RAG) instead of re-authoring them.

Flow
    1. Match every lyric row against lexicon/lexicon.json, longest match first.
    2. Emit a card for every match the lexicon can vouch for, carrying its own
       provenance (reliability, human-confirmed count, source projects).
    3. Leave unmatched and low-confidence spans in project/review/rag-review-queue.json,
       grouped per line as phrase units with candidate glosses attached, for a
       single targeted online review. Nothing is guessed here.

Output cards are marked ``status="rag-reused"`` and stay unapproved until the
user's content decision, exactly like hand-authored drafts.

Usage
    python draft_cards_from_lexicon.py PROJECT_ROOT [--lexicon PATH]
        [--confidence-threshold 0.70] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lexicon_match import DEFAULT_CONFIDENCE_THRESHOLD, KANJI_CHAR_RE, load_lexicon  # noqa: E402

KATAKANA_START, KATAKANA_END, KANA_OFFSET = 0x30A1, 0x30F6, 0x60
KANA_RE = __import__("re").compile(r"^[\u3041-\u3096\u30a1-\u30f6\u30fc]+$")


def to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(c) - KANA_OFFSET) if KATAKANA_START <= ord(c) <= KATAKANA_END else c for c in text
    )


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lexicon_revision(lexicon_path: Path) -> str:
    """Stable identity of the lexicon content: contentSha256 when present, else the file hash."""
    document = load(lexicon_path)
    return str(document.get("contentSha256") or sha(lexicon_path))



def ruby_for(surface: str, reading: str, line: str, occurrence_cursor: int) -> dict | None:
    """Derive a kanji-only ruby span by stripping matching okurigana from both ends."""
    if not reading or not KANA_RE.match(reading):
        return None
    start = 0
    end_surface, end_reading = len(surface), len(reading)
    while start < min(end_surface, end_reading) and surface[start] == reading[start] and not KANJI_CHAR_RE.match(surface[start]):
        start += 1
    while (
        end_surface - 1 > start
        and end_reading - 1 > start
        and surface[end_surface - 1] == reading[end_reading - 1]
        and not KANJI_CHAR_RE.match(surface[end_surface - 1])
    ):
        end_surface -= 1
        end_reading -= 1
    core, core_reading = surface[start:end_surface], reading[start:end_reading]
    if not core or not KANJI_CHAR_RE.search(core) or not core_reading:
        return None
    position = line.find(core, occurrence_cursor)
    if position < 0:
        return None
    return {"base": core, "reading": core_reading, "start": position, "end": position + len(core),
            "_cursor": position + len(core)}


def card_from_span(span: dict) -> dict:
    entry = span
    return {
        "token": span["text"],
        "reading": span["reading"],
        "romaji": span["romaji"],
        "grammarStructureZh": span["grammar"],
        "render": True,
        "status": "rag-reused",
        "reviewRequired": True,
        "fieldProvenance": {
            "token": "matched the project's own lyric text (longest match)",
            "reading": f"lexicon entry {span['entrySurface']} (reliability {span['reliability']})",
            "romaji": f"lexicon entry {span['entrySurface']}",
            "meaningOrFunction": f"lexicon entry {span['entrySurface']}; {span['humanConfirmed']} human-confirmed source(s)",
            "grammarStructureZh": f"lexicon entry {span['entrySurface']}",
        },
        "rag": {
            "entrySurface": span["entrySurface"],
            "matchedBy": span["matchedBy"],
            "confidence": span["confidence"],
            "reliability": span["reliability"],
            "humanConfirmedSources": span["humanConfirmed"],
            "alternateMeanings": span["alternateMeanings"],
        },
        **({"zhMeaning": span["meaning"]} if span["meaningField"] != "functionZh" else {"functionZh": span["meaning"]}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--lexicon", type=Path)
    parser.add_argument("--confidence-threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
                        help=f"Single shared default ({DEFAULT_CONFIDENCE_THRESHOLD}); the matcher and the drafter "
                             "must not disagree or entries fall into a silent reuse gap")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Draft over a frames.json that already carries cards (default: refuse, because the "
                             "queue's framesBeforeSha256 would then describe the previous draft, not the source)")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    lexicon_path = args.lexicon or root.parents[1] / "lexicon" / "lexicon.json"
    lexicon = load_lexicon(lexicon_path)
    frames_path = project / "frames.json"
    document = load(frames_path)
    frames_before = sha(frames_path)
    already_drafted = sum(len(frame.get("grammarCards", [])) for frame in document.get("frames", []))
    if already_drafted and not args.dry_run and not args.force:
        raise SystemExit(
            f"frames.json already carries {already_drafted} card(s); drafting again would record the previous draft "
            "as this run's input. Re-run normalize_lyrics.py into a fresh project, or pass --force if that is intended."
        )

    queue, drafted, reused, review_items = [], 0, 0, 0
    for frame in document.get("frames", []):
        japanese = frame["caption"]["japanese"]
        result = lexicon.match_line(japanese, confidence_threshold=args.confidence_threshold)
        cards, furigana, cursor = [], [], 0
        for span in result["spans"]:
            if span["kind"] == "match" and not span.get("needsReview"):
                cards.append(card_from_span(span))
                ruby = ruby_for(span["entrySurface"], span["reading"], japanese, cursor)
                if ruby:
                    cursor = ruby.pop("_cursor")
                    furigana.append(ruby)
                drafted += 1
        # Matches the lexicon knows but cannot vouch for keep their candidate value
        # as a starting point for the review pass. Matches flagged as fragments of
        # an unknown phrase are deliberately left out: they would appear as
        # meaningless single-character cards (ね/た inside 重ねた) and the phrase
        # unit in the review queue already carries them as hints.
        soft = [
            span for span in result["spans"]
            if span["kind"] == "match" and span.get("needsReview") and not span.get("withinUnknownPhrase")
        ]
        for span in soft:
            cards.append({**card_from_span(span), "status": "rag-proposed-low-confidence",
                          "rag": {**card_from_span(span)["rag"], "reason": "; ".join(span.get("reasons", [])) or "below confidence threshold"}})
        reused += len(soft)
        frame["grammarCards"] = cards
        frame["caption"]["furigana"] = furigana
        if result["reviewUnits"]:
            # One decision per distinct phrase per line: a repeated word (必ず 必ず)
            # is the same review question, and the review artifact identifies a unit
            # as frameId::text. Keeping duplicates would make that identity ambiguous.
            seen_units: set[str] = set()
            units = []
            for unit in result["reviewUnits"]:
                if unit["text"] in seen_units:
                    continue
                seen_units.add(unit["text"])
                units.append(unit)
            review_items += len(units)
            queue.append({
                "frameId": frame["id"],
                "japanese": japanese,
                "translationZh": frame["caption"].get("translationZh", ""),
                "units": units,
                "coverage": result["coverage"],
            })
        frame["status"] = "rag-draft"
        frame["cardReviewStatus"] = "draft"
        frame["reviewRequired"] = True
        frame["fieldProvenance"] = {
            "japanese": "timing/qm.json",
            "romaji": "lexicon reuse where matched, otherwise pending review",
            "translationZh": frame["caption"].get("translationZh", "") and "supplied qmts track",
            "grammarCards": f"lexicon-rag draft ({lexicon_path.name}) with unresolved spans queued for online review",
        }

    document["cardDraft"] = {
        "schemaVersion": 1,
        "authoredBy": ".agent/skills/japanese-song-study-video/scripts/draft_cards_from_lexicon.py",
        "lexicon": {"path": str(lexicon_path.relative_to(root.parents[1])).replace("\\", "/") if lexicon_path.is_relative_to(root.parents[1]) else str(lexicon_path),
                    "sha256": sha(lexicon_path), "entries": len(lexicon.entries), "quarantined": len(lexicon.quarantined)},
        "confidenceThreshold": args.confidence_threshold,
        "status": "rag-draft",
    }
    queue_document = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "framesBeforeSha256": frames_before,
        "lexiconSha256": lexicon_revision(lexicon_path),
        "confidenceThreshold": args.confidence_threshold,
        "totals": {"frames": len(document.get("frames", [])), "cardsDrafted": drafted, "lowConfidenceProposed": reused, "reviewUnits": review_items},
        "instructions": "Review only these units. Each unit lists the fragments the lexicon already knows "
                        "(with candidate meanings) and the unknown text that needs authoring or web verification.",
        "queue": queue,
    }
    if args.dry_run:
        print(json.dumps({"dryRun": True, **queue_document["totals"]}, ensure_ascii=False, indent=2))
        return
    write(project / "review" / "rag-review-queue.json", queue_document)
    write(frames_path, document)
    print(json.dumps({
        "frames": len(document.get("frames", [])),
        "cardsDrafted": drafted,
        "lowConfidenceProposed": reused,
        "reviewUnits": review_items,
        "framesSha256": sha(frames_path),
        "queue": "project/review/rag-review-queue.json",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
