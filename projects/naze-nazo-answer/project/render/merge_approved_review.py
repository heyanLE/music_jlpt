"""Merge the user-approved, lexical-aligned linguistic proposal set."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def by_frame(changes, field):
    return {item["frameId"]: item["new"] for item in changes if item["field"] == field}


def main() -> None:
    before = digest(FRAMES)
    data = load(FRAMES)
    lexical_path = PROJECT / "proposals" / "lexical.json"
    translation_path = PROJECT / "proposals" / "translation-aligned.json"
    grammar_path = PROJECT / "proposals" / "grammar-aligned.json"
    lexical, translation, grammar = load(lexical_path), load(translation_path), load(grammar_path)
    lexical_cards = by_frame(lexical["changes"], "grammarCards")
    lexical_ruby = by_frame(lexical["changes"], "caption.furigana")
    lexical_roma = by_frame(lexical["changes"], "caption.romaji")
    translated_cards = by_frame(translation["changes"], "grammarCards")
    grammar_cards = by_frame(grammar["changes"], "grammarCards")
    translations = by_frame(translation["changes"], "caption.translationZh")
    protected = {"l011", "l032"}
    for frame in data["frames"]:
        fid = frame["id"]
        if fid not in lexical_cards or fid not in translated_cards or fid not in grammar_cards:
            raise RuntimeError(f"missing aligned proposal for {fid}")
        base, semantic, syntax = lexical_cards[fid], translated_cards[fid], grammar_cards[fid]
        if not (len(base) == len(semantic) == len(syntax)):
            raise RuntimeError(f"unaligned card counts for {fid}")
        final_cards = []
        for lex, sem, gram in zip(base, semantic, syntax):
            if lex["token"] != sem["token"] or lex["token"] != gram["token"]:
                raise RuntimeError(f"unaligned token for {fid}")
            card = dict(lex)
            card.update({key: value for key, value in sem.items() if key in ("zhMeaning", "functionZh")})
            card.update({key: value for key, value in gram.items() if key in ("grammarStructureZh", "functionZh")})
            if "functionZh" in card: card.pop("zhMeaning", None)
            if ("zhMeaning" in card) == ("functionZh" in card):
                raise RuntimeError(f"meaning/function invariant failed: {fid} {card['token']}")
            card["posZh"] = card["grammarStructureZh"]
            card["status"] = "assisted-approved"
            card.setdefault("fieldProvenance", {})["meaningOrFunction"] = "translation-aligned assisted proposal accepted"
            card["fieldProvenance"]["grammarStructureZh"] = "grammar-aligned assisted proposal accepted"
            final_cards.append(card)
        frame["grammarCards"] = final_cards
        frame["caption"]["furigana"] = lexical_ruby.get(fid, [])
        frame["caption"]["romaji"] = lexical_roma.get(fid, " ".join(card["romaji"] for card in final_cards))
        if fid not in protected and fid in translations:
            frame["caption"]["translationZh"] = translations[fid]
        frame["status"] = "assisted-approved"
    write(FRAMES, data)
    after = digest(FRAMES)
    merge_log = {"schemaVersion": 2, "framesBeforeSha256": before, "framesAfterSha256": after, "mergedProposalFiles": [str(path.relative_to(ROOT)).replace('\\', '/') for path in (lexical_path, translation_path, grammar_path)], "protectedDecision": "l011/l032 QRC literal and existing Chinese retained by user decision 不改动", "userWording": "确认"}
    write(PROJECT / "review" / "merge-log.json", merge_log)
    audit_sha = digest(PROJECT / "review" / "assisted-review-audit.json")
    decision = {"schemaVersion": 2, "content": "approved", "scope": "all except QRC-literal normalization explicitly declined for l011/l032", "renderAuthorized": False, "userWording": "确认", "frameSha256": after, "assistedReviewAuditSha256": audit_sha, "mergeLogSha256": digest(PROJECT / "review" / "merge-log.json")}
    write(PROJECT / "review" / "review-decision.json", decision)
    lines = ["# なぜ？謎？！ANSWER｜已确认词卡", "", "已采纳多角色审核；l011/l032 按用户决定保留 QQ 歌词原文与既有中文。", ""]
    for frame in data["frames"]:
        lines += [f"## {frame['id']}  {frame['caption']['japanese']}", "", f"- 中文：{frame['caption'].get('translationZh', '')}", "- 词卡："]
        for card in frame["grammarCards"]:
            value = card.get("functionZh", card.get("zhMeaning"))
            lines.append(f"  - {card['token']}｜{card['reading']}｜{card['romaji']}｜{value}｜{card['grammarStructureZh']}")
        lines.append("")
    review = ROOT / "deliverables" / "review" / "naze-nazo-answer-confirmed-review.md"
    review.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(data['frames']), "cards": sum(len(f['grammarCards']) for f in data['frames']), "framesSha256": after, "review": str(review)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
