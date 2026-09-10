"""Integrate role proposals into a review-only full-frame document."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PROJECT / "proposals" / f"{name}.json").read_text(encoding="utf-8"))


def changed_cards(proposal: dict) -> dict[str, list[dict]]:
    return {change["frameId"]: change["new"] for change in proposal["changes"] if change["field"] == "grammarCards"}


def main() -> None:
    frames_path = PROJECT / "frames.json"
    base_sha = sha(frames_path)
    lexical, grammar, translation = load("lexical"), load("grammar"), load("translation")
    for name, proposal in (("lexical", lexical), ("grammar", grammar), ("translation", translation)):
        if proposal.get("baseFrameSha256") != base_sha:
            raise SystemExit(f"{name} proposal is stale")

    frames = json.loads(frames_path.read_text(encoding="utf-8"))["frames"]
    lexical_cards, grammar_cards = changed_cards(lexical), changed_cards(grammar)
    caption_changes = {change["frameId"]: change["new"] for change in translation["changes"] if change["field"] == "caption.translationZh"}
    lexical_furigana = {change["frameId"]: change["new"] for change in lexical["changes"] if change["field"] == "caption.furigana"}
    lexical_romaji = {change["frameId"]: change["new"] for change in lexical["changes"] if change["field"] == "caption.romaji"}

    integrated, conflicts = [], []
    for frame in frames:
        frame_id = frame["id"]
        candidate = copy.deepcopy(frame)
        # Grammar review provides complete meaning/function coverage and more
        # coherent phrase grouping.  Lexical review remains the authority for
        # readings/romaji when both roles retained an identical token.
        cards = copy.deepcopy(grammar_cards.get(frame_id, lexical_cards.get(frame_id, frame.get("grammarCards", []))))
        lexical_by_token = {card["token"]: card for card in lexical_cards.get(frame_id, [])}
        for card in cards:
            lexical_card = lexical_by_token.get(card["token"])
            if lexical_card:
                for field in ("reading", "romaji", "sourceWord"):
                    if lexical_card.get(field):
                        card[field] = lexical_card[field]
            # The visible third card line is deliberately concise.
            card["grammarStructureZh"] = card.get("posZh", "待人工核对")
            if not (card.get("zhMeaning") or card.get("functionZh")):
                card["zhMeaning"] = "待人工核对"
                conflicts.append({"frameId": frame_id, "token": card["token"], "reason": "grammar proposal has no meaning/function"})
            card["status"] = "assisted-proposal"
            card["reviewRequired"] = True
        candidate["grammarCards"] = cards
        candidate["caption"]["translationZh"] = caption_changes.get(frame_id, candidate["caption"].get("translationZh", ""))
        candidate["caption"]["furigana"] = lexical_furigana.get(frame_id, candidate["caption"].get("furigana", []))
        candidate["caption"]["romaji"] = lexical_romaji.get(frame_id, candidate["caption"].get("romaji", ""))
        candidate["status"] = "assisted-proposal"
        integrated.append(candidate)

    output = PROJECT / "review" / "integrated-proposed-frames.json"
    payload = {"schemaVersion": 2, "baseFrameSha256": base_sha, "frames": integrated}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    report = {
        "schemaVersion": 2,
        "reviewRole": "integration",
        "status": "completed",
        "baseFrameSha256": base_sha,
        "sourceProposals": ["project/proposals/lexical.json", "project/proposals/grammar.json", "project/proposals/translation.json"],
        "recommendedProposalSet": "grammar phrase grouping/meanings + lexical exact-token readings/romaji + translation line translations",
        "conflicts": conflicts,
        "recommendation": "Review and explicitly accept the integrated proposal before it replaces project/frames.json.",
    }
    (PROJECT / "review" / "integration-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(integrated), "cards": sum(len(frame["grammarCards"]) for frame in integrated), "conflicts": len(conflicts), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
