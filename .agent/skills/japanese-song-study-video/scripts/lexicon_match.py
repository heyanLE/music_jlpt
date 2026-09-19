#!/usr/bin/env python3
"""Longest-match lookup against the workspace lexicon.

Matching contract
  1. Prefer the longest *surface* match at the cursor (so 明けゆく beats 明け,
     and 二人で would be reused as one card if it were attested).
  2. Fall back to the longest *kana* match (kana-folded, minimum length
     configurable) so a kana-written lyric can still reuse a kanji entry,
     e.g. きみ -> 君, at reduced confidence.
  3. Whitespace and punctuation are separators, never review items.
  4. Anything else becomes an unmatched span that goes to online review.

Each match carries the entry, the match mode, a confidence and a review flag.
Confidence falls when the entry is ambiguous (several attested meanings) or when
reliability is low, so drafting can auto-fill the safe majority and send only
the doubtful spans to a targeted online review.

CLI
    python lexicon_match.py --lexicon lexicon/lexicon.json --text "重ねた 手のひら"
    python lexicon_match.py --lexicon lexicon/lexicon.json --lines-file lines.txt [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

KATAKANA_START, KATAKANA_END, KANA_OFFSET = 0x30A1, 0x30F6, 0x60
# ヽ/ヾ are iteration marks in real lyrics; treating them as non-kana quarantined
# legitimate readings.
KANA_RE = re.compile(r"^[\u3041-\u3096\u30a1-\u30f6\u30fc\u30fd\u30fe]+$")
KANJI_CHAR_RE = re.compile(r"[\u4e00-\u9fff\u3005\u3006]")
LATIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9'\u2019.\-]*$")
# Wave dash, ellipsis and friends are punctuation, not lyric content to review.
SEPARATOR_RE = re.compile(r"[\s\u3000\u3001\u3002\uff01\uff1f\uff0c\uff0e\u30fb\u2018\u2019\u201c\u201d\uff08\uff09\u300c\u300d\u300e\u300f\u301c\uff5e\u2026\u2015\u2014!-/:-@\[-`{-~]")
EXACT_MATCH_FACTOR = 1.0
KANA_MATCH_FACTOR = 0.75
AMBIGUOUS_CONFIDENCE_CAP = 0.6
# One default, shared by every caller: two different thresholds meant entries in the
# gap were "too low" for the matcher but silently reused by the drafter.
DEFAULT_CONFIDENCE_THRESHOLD = 0.75
FUNCTION_MARKERS = ("助词", "助動词", "助动词", "終助詞", "终助词", "副助词", "接续助词", "格助词", "提示助词", "係助词")
# A single character is only reusable when it really is a particle or auxiliary.
# Without the whitelist, dirty one-character drafts (う, え, せ …) shred real words.
SINGLE_CHAR_FUNCTION_WHITELIST = {
    "を", "が", "に", "は", "で", "と", "も", "の", "へ", "や", "か", "ね", "よ", "な",
    "だ", "た", "て", "で", "ず", "ぞ", "ぜ", "さ", "わ", "ん", "ば", "し", "り",
}


def is_function_entry(entry: dict) -> bool:
    """Function words (particles/auxiliaries) may be reused as single characters."""
    surface = entry.get("surface", "")
    if len(surface) == 1:
        if surface not in SINGLE_CHAR_FUNCTION_WHITELIST:
            return False
    grammar = entry.get("dominantGrammar") or ""
    return entry.get("kind") == "particle" or any(marker in grammar for marker in FUNCTION_MARKERS)


def to_hiragana(text: str) -> str:
    return "".join(
        chr(ord(character) - KANA_OFFSET) if KATAKANA_START <= ord(character) <= KATAKANA_END else character
        for character in text
    )


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", str(text))


def is_separator(character: str) -> bool:
    return bool(SEPARATOR_RE.match(character))


def is_latin_token(text: str) -> bool:
    return bool(LATIN_RE.match(text))


class Lexicon:
    """Indexed view over lexicon.json; immutable and cheap to construct.

    Only entries the builder marked ``matchable`` enter the index: quarantined
    entries (whole-line "cards", non-kana readings) stay in the store as
    evidence but can never win a match.
    """

    def __init__(self, document: dict, min_kana_length: int = 2, min_surface_length: int = 2):
        self.document = document
        self.min_kana_length = min_kana_length
        self.min_surface_length = min_surface_length
        self.entries: dict[str, dict] = {
            entry["surface"]: entry for entry in document["entries"] if entry.get("matchable", True)
        }
        self.quarantined = [entry["surface"] for entry in document["entries"] if not entry.get("matchable", True)]
        self.by_surface: dict[str, dict] = {}
        for surface, entry in self.entries.items():
            # A single character is only reusable when it is a function word;
            # otherwise ragged single-kanji/kana drafts would shred real words.
            if len(surface) >= min_surface_length or is_function_entry(entry):
                self.by_surface[surface] = entry
        self.by_kana: dict[str, list[dict]] = {}
        for entry in self.by_surface.values():
            kana = entry.get("kana") or ""
            if not KANA_RE.match(kana):
                continue
            if len(kana) >= min_kana_length or entry.get("surface") == kana:
                self.by_kana.setdefault(kana, []).append(entry)
        self.max_surface = max((len(surface) for surface in self.by_surface), default=1)
        self.max_kana = max((len(kana) for kana in self.by_kana), default=1)

    # -- lookup ---------------------------------------------------------------
    def best_match(self, text: str, index: int) -> dict | None:
        remaining = len(text) - index
        if remaining <= 0:
            return None
        for length in range(min(self.max_surface, remaining), 0, -1):
            entry = self.by_surface.get(text[index:index + length])
            if entry is not None:
                return self._candidate(entry, index, length, "surface", text=text)
        for length in range(min(self.max_kana, remaining), self.min_kana_length - 1, -1):
            slice_text = text[index:index + length]
            if not KANA_RE.match(slice_text):
                continue  # never let Latin or punctuation match a kana key
            candidates = self.by_kana.get(to_hiragana(slice_text))
            if candidates:
                entry = max(candidates, key=lambda item: (item["reliability"]["score"], item["sources"]))
                return self._candidate(entry, index, length, "kana", homophones=candidates, text=text)
        return None

    def _candidate(self, entry: dict, index: int, length: int, mode: str,
                   homophones: list[dict] | None = None, text: str = "") -> dict:
        ambiguity = entry.get("ambiguity", {})
        variants = ambiguity.get("meaningVariants", 1)
        confidence = entry["reliability"]["score"] * (EXACT_MATCH_FACTOR if mode == "surface" else KANA_MATCH_FACTOR)
        reasons = []
        if variants > 1:
            confidence = min(confidence, AMBIGUOUS_CONFIDENCE_CAP)
            reasons.append(f"{variants} attested meanings; pick the one that fits the sentence")
        if not entry.get("dominantMeaning"):
            confidence = min(confidence, 0.3)
            reasons.append("entry has no meaning yet")
        if not entry.get("dominantGrammar"):
            confidence = min(confidence, 0.5)
            reasons.append("entry has no grammar label yet")
        alternatives = []
        if mode == "kana":
            # The line is written differently from the attested surface, so the
            # lexicon cannot decide between homophones on its own. Such a match is a
            # candidate for the reviewer, never something to reuse silently.
            confidence = min(confidence, 0.55)
            reasons.append(f"kana-only match: the line writes {text[index:index + length]!r}, the entry surface is {entry['surface']}")
            if homophones and len(homophones) > 1:
                alternatives = sorted(
                    ({"surface": item["surface"], "meaning": item.get("dominantMeaning", ""),
                      "reliability": item["reliability"]["score"]} for item in homophones if item["surface"] != entry["surface"]),
                    key=lambda item: item["reliability"], reverse=True,
                )[:4]
                confidence = min(confidence, 0.4)
                reasons.append(f"{len(homophones)} entries share this kana form; candidates: "
                               + ", ".join(item["surface"] for item in alternatives))
        return {
            "entry": entry,
            "start": index,
            "end": index + length,
            "surface": entry["surface"],
            "sourceText": entry["surface"],
            "matchedBy": mode,
            "confidence": round(confidence, 3),
            "reasons": reasons,
            "alternatives": alternatives,
            "forceReview": mode == "kana",
        }

    # -- segmentation ---------------------------------------------------------
    def hints_for(self, text: str, start: int, end: int, limit: int = 4) -> list[dict]:
        """Reuse hints for an unmatched run.

        Single-character content entries are kept out of the match index (they
        shred real words), but a reviewer still benefits from knowing that the
        lexicon already has 夜 = 夜晚. Hints never drive segmentation.
        """
        hints: list[dict] = []
        seen: set[str] = set()
        for position in range(start, end):
            for length in range(min(6, end - position), 0, -1):
                entry = self.entries.get(text[position:position + length])
                if entry is None or entry["surface"] in seen:
                    continue
                seen.add(entry["surface"])
                hints.append({
                    "surface": entry["surface"],
                    "meaning": entry.get("dominantMeaning", ""),
                    "grammar": entry.get("dominantGrammar", ""),
                    "reliability": entry["reliability"]["score"],
                    "start": position,
                })
                if len(hints) >= limit:
                    return hints
        return hints

    def match_line(self, text: str, confidence_threshold: float = 0.75, merge: bool = False) -> dict:
        text = normalise(text)
        spans: list[dict] = []
        index = 0
        while index < len(text):
            character = text[index]
            if is_separator(character):
                end = index + 1
                while end < len(text) and is_separator(text[end]):
                    end += 1
                spans.append({"kind": "separator", "start": index, "end": end, "text": text[index:end]})
                index = end
                continue
            if character.isascii() and (character.isalnum() or character in "'\u2019"):
                # English/Latin runs keep their position and highlighting but take
                # no card, ruby or romaji, so they are neither matched nor reviewed.
                # An inner apostrophe or hyphen (don't, well-known) stays part of the
                # token instead of silently splitting it.
                end = index
                while end < len(text):
                    char = text[end]
                    if char.isascii() and char.isalnum():
                        end += 1
                    elif char in "'\u2019-" and index < end < len(text) - 1 and text[end - 1].isascii() and text[end - 1].isalnum() and text[end + 1].isascii() and text[end + 1].isalnum():
                        end += 1
                    else:
                        break
                if end <= index:
                    end = index + 1
                spans.append({"kind": "latin", "start": index, "end": end, "text": text[index:end]})
                index = end
                continue
            candidate = self.best_match(text, index)
            if candidate is None:
                end = index + 1
                while end < len(text) and not is_separator(text[end]) and not text[end].isascii() and self.best_match(text, end) is None:
                    end += 1
                spans.append({
                    "kind": "unmatched", "start": index, "end": end, "text": text[index:end],
                    "hints": self.hints_for(text, index, end),
                })
                index = end
                continue
            entry = candidate.pop("entry")
            spans.append({
                "kind": "match",
                **candidate,
                "text": text[candidate["start"]:candidate["end"]],
                "entrySurface": entry["surface"],
                "reading": entry.get("dominantReading", ""),
                "romaji": entry.get("dominantRomaji", ""),
                "meaning": entry.get("dominantMeaning", ""),
                "meaningField": entry.get("meaningField", ""),
                "grammar": entry.get("dominantGrammar", ""),
                "grammarField": entry.get("grammarField", ""),
                "entryKind": entry.get("kind", "unknown"),
                "alternateMeanings": [variant["value"] for variant in entry.get("meanings", [])[1:]],
                "homophoneAlternatives": candidate.get("alternatives", []),
                "reliability": entry["reliability"]["score"],
                "humanConfirmed": entry.get("humanConfirmed", 0),
                "needsReview": bool(candidate.get("forceReview"))
                or candidate["confidence"] < confidence_threshold
                or not entry.get("dominantMeaning"),
            })
            index = candidate["end"]
        if merge:
            spans = merge_fragments(spans, text)
        phrase_units = annotate_review_units(spans, text)
        content_spans = [span for span in spans if span["kind"] in ("match", "unmatched")]
        matched = [span for span in content_spans if span["kind"] == "match"]
        review = [span for span in content_spans if span["kind"] == "unmatched" or span.get("needsReview")]
        return {
            "text": text,
            "spans": spans,
            "coverage": {
                "contentSpans": len(content_spans),
                "matchedSpans": len(matched),
                "unmatchedSpans": sum(1 for span in content_spans if span["kind"] == "unmatched"),
                "latinSpans": sum(1 for span in spans if span["kind"] == "latin"),
                "mergedFragments": sum(1 for span in spans if span.get("mergedFragments")),
                "matchedCharacters": sum(span["end"] - span["start"] for span in matched),
                "contentCharacters": sum(span["end"] - span["start"] for span in content_spans),
                "ratio": round(
                    sum(span["end"] - span["start"] for span in matched) / max(1, sum(span["end"] - span["start"] for span in content_spans)), 3
                ),
                "autoFillable": sum(1 for span in matched if not span.get("needsReview")),
                "reviewUnits": len(phrase_units),
            },
            "reviewUnits": phrase_units,
            "reviewQueue": [
                {
                    "text": span["text"],
                    "start": span["start"],
                    "end": span["end"],
                    "reason": "not in lexicon (fragments merged)" if span.get("mergedFragments")
                    else "not in lexicon" if span["kind"] == "unmatched"
                    else "; ".join(span.get("reasons", [])) or "low confidence",
                    "candidates": [span["meaning"]] + span.get("alternateMeanings", []) if span["kind"] == "match" else [],
                    "hints": span.get("hints", []),
                    "fragmentHints": span.get("fragmentHints", []),
                    "withinUnknownPhrase": span.get("withinUnknownPhrase", False),
                }
                for span in review
            ],
        }


def annotate_review_units(spans: list[dict], text: str) -> list[dict]:
    """Group each run that contains unknown text into one phrase-level review unit.

    Word boundaries are unknowable from a card store alone, so a run such as
    重 + ね + た (where 重ねた is unknown) must be reviewed as one phrase rather
    than as three independent items. The spans themselves stay granular so a
    draft step can still reuse the parts it trusts; only the review queue is
    grouped, and the grouped parts are marked so nothing is auto-filled inside
    an unknown phrase.
    """
    units: list[dict] = []
    run: list[dict] = []

    def flush() -> None:
        nonlocal run
        if run and any(span["kind"] == "unmatched" for span in run):
            start, end = run[0]["start"], run[-1]["end"]
            for index, span in enumerate(run):
                if span["kind"] != "match":
                    continue
                # A two-or-more character exact match is self-validating: it is
                # real evidence of a word, so it stays reusable even when the
                # surrounding run also contains unknown text. Only single
                # characters (which may just be fragments of an unknown word,
                # like ね/た inside 重ねた) are demoted to review.
                if span["end"] - span["start"] < 2 and (index > 0 or index < len(run) - 1):
                    span["needsReview"] = True
                    span["withinUnknownPhrase"] = True
            units.append({
                "kind": "phrase",
                "text": text[start:end],
                "start": start,
                "end": end,
                "parts": [
                    {
                        "text": span["text"],
                        "matched": span["kind"] == "match",
                        "entrySurface": span.get("entrySurface"),
                        "meaning": span.get("meaning"),
                        "grammar": span.get("grammar"),
                        "candidates": ([span["meaning"]] + span.get("alternateMeanings", [])) if span["kind"] == "match" else [],
                        "hints": span.get("hints", []),
                    }
                    for span in run
                ],
            })
        run = []

    for span in spans:
        if span["kind"] in ("separator", "latin"):
            flush()
        else:
            run.append(span)
    flush()
    return units


def load_lexicon(path: Path, min_kana_length: int = 2, min_surface_length: int = 2) -> Lexicon:
    return Lexicon(json.loads(path.read_text(encoding="utf-8")), min_kana_length=min_kana_length, min_surface_length=min_surface_length)


def merge_fragments(spans: list[dict], text: str) -> list[dict]:
    """Join ragged runs into one review unit.

    Greedy longest match cannot know word boundaries, so an unknown word such as
    愛おしい arrives as [愛(match)][お(unmatched)][し(match)][い(unmatched)]. Such a
    run - unmatched text mixed with single-character matches - is meaningless as
    separate cards, so it becomes one review unit whose hints keep the fragments
    the lexicon did recognise. A run of single-character matches with no
    unmatched text (a real particle sequence) is left alone.
    """
    def joinable(span: dict) -> bool:
        return span["kind"] == "unmatched" or (span["kind"] == "match" and span["end"] - span["start"] == 1)

    runs: list[list[dict]] = []
    for span in spans:
        if span["kind"] in ("separator", "latin"):
            runs.append([span])
        elif runs and joinable(span) and joinable(runs[-1][-1]):
            runs[-1].append(span)
        else:
            runs.append([span])

    output: list[dict] = []
    for run in runs:
        has_unmatched = any(span["kind"] == "unmatched" for span in run)
        if len(run) > 1 and has_unmatched:
            start, end = run[0]["start"], run[-1]["end"]
            output.append({
                "kind": "unmatched",
                "start": start,
                "end": end,
                "text": text[start:end],
                "mergedFragments": True,
                "fragmentHints": [
                    {"text": span["text"], "entrySurface": span["entrySurface"], "meaning": span["meaning"], "grammar": span["grammar"]}
                    for span in run if span["kind"] == "match"
                ],
            })
        else:
            output.extend(run)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexicon", type=Path, required=True)
    parser.add_argument("--text")
    parser.add_argument("--lines-file", type=Path)
    parser.add_argument("--confidence-threshold", type=float, default=0.75)
    parser.add_argument("--min-kana-length", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    lexicon = load_lexicon(args.lexicon, min_kana_length=args.min_kana_length)
    texts: list[str] = []
    if args.text:
        texts.append(args.text)
    if args.lines_file:
        texts.extend(line.rstrip("\n") for line in args.lines_file.read_text(encoding="utf-8").splitlines() if line.strip())
    if not texts:
        raise SystemExit("Provide --text or --lines-file")

    results = [lexicon.match_line(text, confidence_threshold=args.confidence_threshold) for text in texts]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    for result in results:
        queue = result["reviewQueue"]
        print(f"\n{result['text']}")
        print(f"  coverage {result['coverage']['ratio']:.0%}  matched={result['coverage']['matchedSpans']}  auto={result['coverage']['autoFillable']}  latin={result['coverage']['latinSpans']}  review={len(queue)}")
        for span in result["spans"]:
            if span["kind"] in ("separator", "latin"):
                continue
            if span["kind"] == "unmatched":
                print(f"   [ review ] {span['text']}  (not in lexicon)")
            else:
                flag = "review" if span["needsReview"] else "auto  "
                print(f"   [{flag} ] {span['text']:<12} {span['reading']:<12} {span['meaning']:<18} {span['grammar']:<22} conf={span['confidence']:.2f} matchedBy={span['matchedBy']}")


if __name__ == "__main__":
    main()
