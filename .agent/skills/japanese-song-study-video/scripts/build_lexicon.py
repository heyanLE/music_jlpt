#!/usr/bin/env python3
"""Aggregate every project's cards into the workspace lexicon (reuse layer for drafting).

Two different things are deliberately NOT conflated:

* **variants** - one surface legitimately carries several meanings/usages across
  sentences (particles, 永遠 read えいえん or とわ). All attested variants are kept
  with their own counters, and the entry exposes a *dominant* pick plus an
  ambiguity count so drafting can send multi-variant entries to online review
  instead of guessing.
* **conflicts** - the same field claimed differently by sources. Here the newest
  source wins (user decision, 2026-09-11), with a human-confirmed source beating
  a draft one inside the same second.

Usage
    python build_lexicon.py [WORKSPACE_ROOT] [--out lexicon/lexicon.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 2
MAX_PROVENANCE = 8           # bound per-entry provenance; the totals stay in counters
MAX_VARIANTS = 12            # bound exotic surfaces; truncation is reported
KATAKANA_START, KATAKANA_END, KANA_OFFSET = 0x30A1, 0x30F6, 0x60
KANA_RE = re.compile(r"^[\u3041-\u3096\u30a1-\u30f6\u30fc\u30fd\u30fe]+$")
JAPANESE_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30f6\u30fc\u4e00-\u9fff\u3005\u3006]")
KANJI_RE = re.compile(r"[\u4e00-\u9fff\u3005\u3006]")
MAX_MATCHABLE_LENGTH = 20   # a reusable card chunk, not a whole lyric line
FUNCTION_MARKERS = ("助词", "助動词", "助动词", "終助詞", "终助词", "副助词", "接续助词", "格助词", "提示助词", "係助词")
VARIANT_FIELDS = ("meaning", "grammar", "reading", "romaji")
SCALAR_FIELDS = ("dictionaryForm", "sourceWord", "showJlpt", "kind", "meaningField", "grammarField")


def quality_issues(surface: str, reading: str, kana: str) -> list[str]:
    """Detect entries whose stored fields cannot be trusted for automatic reuse.

    Historical projects contain whole-line "cards" whose reading holds only the
    first mora (``i``, ``ya``, ``ko``), and a few non-Japanese surfaces. Those
    entries stay in the lexicon as evidence but are excluded from the match
    index so they can never silently overwrite a real chunk match.
    """
    issues = []
    if not JAPANESE_RE.search(surface):
        issues.append("no-japanese-characters")
    if len(surface) > MAX_MATCHABLE_LENGTH:
        issues.append(f"surface-longer-than-{MAX_MATCHABLE_LENGTH}")
    if reading and not KANA_RE.match(reading):
        issues.append("reading-not-kana")
    if KANJI_RE.search(surface):
        if not reading:
            issues.append("kanji-without-reading")
        elif len(reading) < len(KANJI_RE.findall(surface)):
            issues.append("reading-shorter-than-kanji-count")
    if kana and not KANA_RE.match(kana):
        issues.append("kana-key-not-kana")
    return issues


def to_hiragana(text: str) -> str:
    """Fold katakana to hiragana so ボク and ぼく share one lookup key."""
    return "".join(
        chr(ord(character) - KANA_OFFSET) if KATAKANA_START <= ord(character) <= KATAKANA_END else character
        for character in text
    )


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", str(text)).strip()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def card_fields(card: dict) -> dict:
    """Map the historical card variants (grammarStructureZh/posZh, zhMeaning/functionZh) onto one record."""
    if card.get("grammarStructureZh"):
        grammar, grammar_field = normalise(card["grammarStructureZh"]), "grammarStructureZh"
    elif card.get("posZh"):
        grammar, grammar_field = normalise(card["posZh"]), "posZh"
    else:
        grammar, grammar_field = "", ""
    if card.get("zhMeaning"):
        meaning, meaning_field, kind = normalise(card["zhMeaning"]), "zhMeaning", "content"
    elif card.get("functionZh"):
        meaning, meaning_field, kind = normalise(card["functionZh"]), "functionZh", "particle"
    else:
        meaning, meaning_field, kind = "", "", "unknown"
    return {
        "meaning": meaning, "meaningField": meaning_field, "kind": kind,
        "grammar": grammar, "grammarField": grammar_field,
        "reading": normalise(card.get("reading", "")),
        "romaji": str(card.get("romaji", "")).strip(),
        "dictionaryForm": normalise(card.get("dictionaryForm", "")),
        "sourceWord": normalise(card.get("sourceWord", "")),
        "showJlpt": card.get("showJlpt") if isinstance(card.get("showJlpt"), bool) else None,
    }


def dedupe_senses(value: str) -> str:
    """Drop repeated senses inside one value.

    A sense list is legitimately separated by ；(远远地；遥远), but a stored value can carry
    the same sense several times (a card once read 看得见；看得见；看得见), and reusing that
    would print the repetition in every later project.
    """
    if "；" not in value and ";" not in value:
        return value
    seen, parts = set(), []
    for part in re.split(r"[；;]", value):
        stripped = part.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            parts.append(stripped)
    return "；".join(parts) if parts else value


def add_variant(bucket: dict[str, dict], value: str, recorded_at: str, confirmed: bool, project: str, rank: int,
                pinned: bool = False) -> None:
    value = dedupe_senses(value)
    if not value:
        return
    record = bucket.setdefault(value, {"value": value, "count": 0, "humanConfirmed": 0, "lastSeenAt": recorded_at, "recencyRank": rank, "projects": set()})
    record["count"] += 1
    record["humanConfirmed"] += int(confirmed)
    record["projects"].add(project)
    if pinned:
        record["pinned"] = True
    if project == "reviewed-correction":
        record["reviewedCorrections"] = record.get("reviewedCorrections", 0) + 1
    if rank >= record.get("recencyRank", -1):
        record["recencyRank"] = rank
        record["lastSeenAt"] = recorded_at
        record["newestHumanConfirmed"] = confirmed


def variant_rank(record: dict) -> tuple:
    """Ranking for the dominant pick: an explicit user pin first, then attested
    content, then human-confirmed, frequency and recency.

    A value that exists *only* because of a reviewed correction never becomes dominant.
    A correction is how a context-dependent reading enters the store - 溢れる read as
    こぼれる is a 義訓 in one line while あふれる stays the normal reading everywhere
    else - so promoting it would silently rewrite every later project. It still counts
    as an attested variant, and the extra variant raises the entry's ambiguity so the
    matcher sends the word to review.

    The one thing that outranks frequency is a **pin**: the scalar form in
    ``overrides.json`` (``"ない": {"meaning": "..."}``) is the user's own statement
    about the dominant value, not one more attestation. Frequency is a poor proxy for
    truth when the losing value was voted for by dirty drafts - ない carried 没有 in
    dozens of drafts before the user ruled it an auxiliary in this context - and a
    correction alone can never overtake that lead. Pinning is the escape hatch, and
    it is deliberately rare: it rewrites every later project's prefill, so it needs a
    decision, not a hunch.
    """
    attested = 1 if record["count"] > record.get("reviewedCorrections", 0) else 0
    return (1 if record.get("pinned") else 0, attested, 1 if record["humanConfirmed"] else 0,
            record["count"], record.get("recencyRank", 0), record["lastSeenAt"])


def serialise_variants(bucket: dict[str, dict]) -> list[dict]:
    ordered = sorted(bucket.values(), key=variant_rank, reverse=True)
    output = []
    for record in ordered[:MAX_VARIANTS]:
        item = {
            "value": record["value"],
            "count": record["count"],
            "humanConfirmed": record["humanConfirmed"],
            "projects": len(record["projects"]),
            "lastSeenAt": record["lastSeenAt"],
            "recencyRank": record.get("recencyRank", 0),
            "reviewedCorrections": record.get("reviewedCorrections", 0),
        }
        # Only the pin is flagged, so a dominant value that contradicts the frequency
        # leader is explainable from lexicon.json alone.
        if record.get("pinned"):
            item["pinned"] = True
        output.append(item)
    return output


def resolve_project_order(root: Path, discovered: dict[str, float], order_path: Path, refresh: bool) -> list[str]:
    """Recency must not depend on filesystem mtimes, which reset on clone.

    The order is persisted in lexicon/project-order.json; newly discovered
    projects are appended (by mtime within the batch) so they count as newest.
    """
    if order_path.is_file() and not refresh:
        order = list(load_json(order_path).get("order", []))
    else:
        order = []
    known = set(order)
    fresh = [slug for slug in discovered if slug not in known]
    order.extend(sorted(fresh, key=lambda slug: discovered[slug]))
    document = {
        "schemaVersion": 1,
        "note": "Recency order for the newest-wins conflict rule. Append-only; new projects are appended automatically.",
        "order": order,
    }
    order_path.parent.mkdir(parents=True, exist_ok=True)
    order_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return order


def is_function_entry(entry: dict) -> bool:
    """Function words carry several genuinely different uses; content words do not."""
    grammar = entry.get("dominantGrammar") or ""
    return entry.get("kind") == "particle" or any(marker in grammar for marker in FUNCTION_MARKERS)


def score_entry(entry: dict) -> float:
    """Deterministic reliability seed; apply_lexicon_feedback.py moves it afterwards.

    The seed only has to be reasonable for the first run - the user's accept and
    reject decisions are what actually calibrate an entry (see lexicon/README.md).

    Ambiguity is penalised differently by word class: several attested *uses* of a
    particle are a real decision (it must be picked per sentence), while several
    glosses of a content word are usually paraphrases of one sense and stay
    reusable.
    """
    confirmed = entry["humanConfirmed"]
    projects = entry["projectCount"]
    if confirmed:
        score = 0.90
    elif projects >= 2:
        score = 0.72
    else:
        score = 0.60
    if not confirmed:
        score += min(0.06, 0.02 * max(0, projects - 1))
    if not entry["dominantGrammar"]:
        score -= 0.10
    if not entry["dominantMeaning"]:
        score -= 0.20
    extra_meanings = max(0, entry["ambiguity"]["meaningVariants"] - 1)
    if is_function_entry(entry):
        score -= min(0.25, 0.05 * extra_meanings)
    else:
        score -= min(0.06, 0.02 * extra_meanings)
    score -= min(0.10, 0.05 * max(0, entry["ambiguity"]["grammarVariants"] - 1))
    # User feedback moves an entry up or down; this is what actually calibrates
    # reuse over time (see apply_lexicon_feedback.py and lexicon/README.md).
    # Scoring is net-based so an entry the user later accepted repeatedly recovers
    # instead of being pinned down by old rejections, while a net-rejected entry
    # stays low.
    accepts, rejects = entry.get("accepts", 0), entry.get("rejects", 0)
    if accepts > rejects:
        score = max(score, min(0.98, 0.85 + 0.02 * (accepts - rejects)))
    score -= min(0.40, 0.15 * max(0, rejects - accepts))
    return round(max(0.0, min(1.0, score)), 3)


def stable_projection(value):
    """Drop wall-clock fields so contentSha256 depends on content, not on clone time."""
    if isinstance(value, dict):
        return {key: stable_projection(item) for key, item in value.items()
                if key not in ("lastSeenAt", "recordedAt", "generatedAt", "sealedAt")}
    if isinstance(value, list):
        return [stable_projection(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace_root", nargs="?", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--projects-glob", default="projects/*/project/frames.json")
    parser.add_argument("--refresh-order", action="store_true", help="Recompute the persisted project recency order from filesystem mtimes")
    parser.add_argument("--exclude", action="append", default=[], help="Project slug to leave out (repeatable); use for honest leave-one-out coverage tests")
    args = parser.parse_args()

    root = args.workspace_root.resolve()
    out = (args.out or root / "lexicon" / "lexicon.json").resolve()
    try:
        out.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"--out must stay inside the workspace ({root}): {out}") from exc
    overrides_path = root / "lexicon" / "overrides.json"
    feedback_path = root / "lexicon" / "feedback.json"
    order_path = root / "lexicon" / "project-order.json"

    frame_paths = [path for path in sorted(root.glob(args.projects_glob)) if path.parents[1].name not in set(args.exclude)]
    discovered = {path.parents[1].name: path.stat().st_mtime for path in frame_paths}
    order = resolve_project_order(root, discovered, order_path, args.refresh_order)
    rank_of = {slug: index for index, slug in enumerate(order)}

    entries: dict[str, dict] = {}
    scanned, skipped = 0, []

    for frames_path in frame_paths:
        slug = frames_path.parents[1].name
        rank = rank_of.get(slug, len(order))
        try:
            document = load_json(frames_path)
        except Exception as exc:  # noqa: BLE001 - report and continue
            skipped.append(f"{slug}: {type(exc).__name__}: {exc}")
            continue
        recorded_at = datetime.fromtimestamp(frames_path.stat().st_mtime, tz=timezone.utc).isoformat()
        scanned += 1
        for frame in document.get("frames", []):
            for card in frame.get("grammarCards", []):
                surface = normalise(card.get("token", ""))
                if not surface:
                    continue
                fields = card_fields(card)
                confirmed = str(card.get("status", "")) == "human-confirmed"
                entry = entries.setdefault(surface, {
                    "surface": surface,
                    "kana": to_hiragana(surface) if KANA_RE.match(surface) else "",
                    "variants": {field: {} for field in VARIANT_FIELDS},
                    "scalars": {},
                    "provenance": [],
                    "counters": {"sources": 0, "humanConfirmed": 0, "projects": set()},
                    "recencyRank": rank,
                    "lastSeenAt": recorded_at,
                    "lastSeenHumanConfirmed": confirmed,
                })
                entry["counters"]["sources"] += 1
                entry["counters"]["humanConfirmed"] += int(confirmed)
                entry["counters"]["projects"].add(slug)
                entry["provenance"].append({"project": slug, "frameId": frame.get("id"), "status": card.get("status", "draft"), "recencyRank": rank, "recordedAt": recorded_at})
                newer = (rank, confirmed) >= (entry["recencyRank"], entry["lastSeenHumanConfirmed"])
                if newer:
                    entry["recencyRank"], entry["lastSeenAt"], entry["lastSeenHumanConfirmed"] = rank, recorded_at, confirmed
                for field in VARIANT_FIELDS:
                    add_variant(entry["variants"][field], fields[field], recorded_at, confirmed, slug, rank)
                for field in SCALAR_FIELDS:
                    if fields[field] in (None, ""):
                        continue
                    current = entry["scalars"].get(field)
                    if current is None or (rank, confirmed) >= (current["recencyRank"], current["status"] == "human-confirmed"):
                        entry["scalars"][field] = {"value": fields[field], "project": slug, "recencyRank": rank, "recordedAt": recorded_at, "status": card.get("status", "draft")}
                if not entry["kana"]:
                    reading = fields["reading"]
                    if reading:
                        entry["kana"] = to_hiragana(reading)

    feedback = load_json(feedback_path) if feedback_path.is_file() else {"entries": {}}
    overrides = load_json(overrides_path) if overrides_path.is_file() else {"entries": {}}

    output_entries = []
    for surface, entry in entries.items():
        override = overrides.get("entries", {}).get(surface, {})
        feedback_entry = feedback.get("entries", {}).get(surface, {})
        # A reviewed correction is an extra attested variant, not a replacement:
        # polysemous particles keep every function that has been observed.
        for correction in override.get("corrections", []):
            field = correction.get("field")
            if field in VARIANT_FIELDS and correction.get("value"):
                add_variant(entry["variants"][field], normalise(correction["value"]),
                            correction.get("at") or datetime.now(timezone.utc).isoformat(), True, "reviewed-correction", len(order) + 1)
        for field in VARIANT_FIELDS:
            if field in override and not isinstance(override[field], dict):
                # Scalar form = the user's own decision about the dominant value, so it
                # is pinned (ranked first) instead of competing on frequency. The
                # timestamp is the file's mtime: a pin has no per-correction date.
                stamp = datetime.fromtimestamp(overrides_path.stat().st_mtime, tz=timezone.utc).isoformat()
                add_variant(entry["variants"][field], normalise(override[field]), stamp, True, "override",
                            len(order) + 1, pinned=True)
        serialised = {field: serialise_variants(entry["variants"][field]) for field in VARIANT_FIELDS}
        ambiguity = {
            "meaningVariants": len(serialised["meaning"]),
            "grammarVariants": len(serialised["grammar"]),
            "readingVariants": len(serialised["reading"]),
        }
        record = {
            "surface": surface,
            "kana": entry["kana"] or (to_hiragana(serialised["reading"][0]["value"]) if serialised["reading"] else ""),
            "kind": (entry["scalars"].get("kind") or {}).get("value", "unknown"),
            "dominantMeaning": serialised["meaning"][0]["value"] if serialised["meaning"] else "",
            "dominantGrammar": serialised["grammar"][0]["value"] if serialised["grammar"] else "",
            "dominantReading": serialised["reading"][0]["value"] if serialised["reading"] else "",
            "dominantRomaji": serialised["romaji"][0]["value"] if serialised["romaji"] else "",
            "meaningField": (entry["scalars"].get("meaningField") or {}).get("value", ""),
            "grammarField": (entry["scalars"].get("grammarField") or {}).get("value", ""),
            "dictionaryForm": (entry["scalars"].get("dictionaryForm") or {}).get("value", ""),
            "sourceWord": (entry["scalars"].get("sourceWord") or {}).get("value", ""),
            "showJlpt": (entry["scalars"].get("showJlpt") or {}).get("value"),
            "meanings": serialised["meaning"],
            "grammars": serialised["grammar"],
            "readings": serialised["reading"],
            "romajis": serialised["romaji"],
            "sources": entry["counters"]["sources"],
            "humanConfirmed": entry["counters"]["humanConfirmed"],
            "projectCount": len(entry["counters"]["projects"]),
            "accepts": int(feedback_entry.get("accepts", 0)),
            "rejects": int(feedback_entry.get("rejects", 0)),
            "ambiguity": ambiguity,
            "recencyRank": entry["recencyRank"],
            "lastSeenAt": entry["lastSeenAt"],
        }
        issues = quality_issues(record["surface"], record["dominantReading"], record["kana"])
        record["qualityIssues"] = issues
        record["matchable"] = not issues
        if "reliability" in override:
            record["reliability"] = {"score": float(override["reliability"]), "pinnedBy": "overrides.json"}
        else:
            record["reliability"] = {"score": score_entry(record)}
        record["reliability"].update({
            "sources": record["sources"],
            "humanConfirmedSources": record["humanConfirmed"],
            "distinctProjects": record["projectCount"],
            "accepts": record["accepts"],
            "rejects": record["rejects"],
            "lastSeenAt": record["lastSeenAt"],
        })
        provenance = sorted(entry["provenance"], key=lambda item: item["recordedAt"], reverse=True)
        record["provenance"] = provenance[:MAX_PROVENANCE]
        record["provenanceTruncated"] = max(0, len(provenance) - MAX_PROVENANCE)
        output_entries.append(record)

    output_entries.sort(key=lambda item: (-len(item["surface"]), item["surface"]))
    entries_sha = hashlib.sha256(
        json.dumps(stable_projection(output_entries), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    document = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "contentSha256": entries_sha,
        "generatedBy": ".agent/skills/japanese-song-study-video/scripts/build_lexicon.py",
        "conflictRule": "newest source wins per field; a human-confirmed source breaks same-second ties",
        "variantRule": "all attested meanings/grammars/readings are kept; the dominant pick is human-confirmed > frequency > recency",
        "matchingContract": "longest surface first, then longest kana form; see scripts/lexicon_match.py",
        "recencyOrder": "lexicon/project-order.json (append-only; never derived from mtimes at read time)",
        "stats": {
            "projectsScanned": scanned,
            "projectsSkipped": skipped,
            "entries": len(output_entries),
            "humanConfirmedEntries": sum(1 for item in output_entries if item["humanConfirmed"]),
            "particleEntries": sum(1 for item in output_entries if item["kind"] == "particle"),
            "unambiguousEntries": sum(1 for item in output_entries if item["ambiguity"]["meaningVariants"] == 1),
            "multiMeaningEntries": sum(1 for item in output_entries if item["ambiguity"]["meaningVariants"] > 1),
            "largestAmbiguity": max((item["ambiguity"]["meaningVariants"] for item in output_entries), default=0),
            "matchableEntries": sum(1 for item in output_entries if item["matchable"]),
            "quarantinedEntries": sum(1 for item in output_entries if not item["matchable"]),
            "quarantineReasons": dict(sorted(
                (reason, sum(1 for item in output_entries if reason in item["qualityIssues"]))
                for reason in {reason for item in output_entries for reason in item["qualityIssues"]}
            )),
            "overridesApplied": len(overrides.get("entries", {})),
            "feedbackApplied": len(feedback.get("entries", {})),
        },
        "entries": output_entries,
    }
    write_json(out, document)
    print(json.dumps({
        "output": str(out.relative_to(root)).replace("\\", "/"),
        "contentSha256": entries_sha,
        "deterministic": "contentSha256 covers the entries; generatedAt is the only wall-clock field",
        "sizeKB": round(out.stat().st_size / 1024),
        "stats": document["stats"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
