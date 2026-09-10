from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cards_by_frame(proposal: dict) -> dict[str, list[dict]]:
    return {change["frameId"]: change["new"] for change in proposal["changes"] if change["field"] == "grammarCards"}


def main() -> None:
    frames_path = PROJECT / "frames.json"
    base_sha = sha(frames_path)
    files = {
        "lexical": PROJECT / "proposals" / "lexical-v2.json",
        "grammar": PROJECT / "proposals" / "grammar-v2.json",
        "translation": PROJECT / "proposals" / "translation-v2.json",
    }
    proposals = {role: json.loads(path.read_text(encoding="utf-8")) for role, path in files.items()}
    for role, proposal in proposals.items():
        if proposal.get("baseFrameSha256") != base_sha:
            raise SystemExit(f"stale {role} proposal")
    lexical_cards = cards_by_frame(proposals["lexical"])
    grammar_cards = cards_by_frame(proposals["grammar"])
    translation_cards = cards_by_frame(proposals["translation"])
    lexical_furigana = {change["frameId"]: change["new"] for change in proposals["lexical"]["changes"] if change["field"] == "caption.furigana"}
    frames = json.loads(frames_path.read_text(encoding="utf-8"))["frames"]
    combined_frames, disagreements = [], []
    for frame in frames:
        frame_id = frame["id"]
        base_cards = copy.deepcopy(lexical_cards[frame_id])
        grammar_index = {card["token"]: card for card in grammar_cards[frame_id]}
        translation_index = {card["token"]: card for card in translation_cards[frame_id]}
        for card in base_cards:
            token = card["token"]
            grammar = grammar_index.get(token)
            translation = translation_index.get(token)
            if grammar:
                card["posZh"] = grammar.get("posZh", card.get("posZh", ""))
            if translation:
                for field in ("zhMeaning", "functionZh"):
                    if field in translation:
                        card.pop("functionZh" if field == "zhMeaning" else "zhMeaning", None)
                        card[field] = translation[field]
            card["grammarStructureZh"] = card.get("posZh", "")
            card["fieldProvenance"] = {
                "token": "lexical-v2",
                "reading": "lexical-v2",
                "romaji": "lexical-v2",
                "meaningOrFunction": "translation-v2 exact-token overlay or lexical-v2",
                "posZh": "grammar-v2 exact-token overlay or lexical-v2",
            }
            card["status"] = "assisted-proposal"
        grammar_unmatched = [card["token"] for card in grammar_cards[frame_id] if card["token"] not in {c["token"] for c in base_cards}]
        translation_unmatched = [card["token"] for card in translation_cards[frame_id] if card["token"] not in {c["token"] for c in base_cards}]
        if grammar_unmatched or translation_unmatched:
            disagreements.append({"frameId": frame_id, "grammarOnlyTokens": grammar_unmatched, "translationOnlyTokens": translation_unmatched, "resolution": "lexical-v2 tokenization selected for complete coverage, compact card count, readings and romaji"})
        combined_frames.append({
            "id": frame_id,
            "caption": frame["caption"],
            "furigana": lexical_furigana.get(frame_id, []),
            "grammarCards": base_cards,
        })
    combined = {"schemaVersion": 1, "baseFrameSha256": base_sha, "selection": "lexical-v2 card segmentation; grammar-v2 POS and translation-v2 meaning/function exact-token overlays", "frames": combined_frames}
    out = PROJECT / "review" / "full-card-proposed-frames.json"
    out.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    integration = {
        "schemaVersion": 2,
        "reviewRole": "integration",
        "status": "completed",
        "baseFrameSha256": base_sha,
        "sourceProposals": [str(path.relative_to(ROOT)).replace("\\", "/") for path in files.values()],
        "conflicts": disagreements,
        "recommendedProposalSet": ["project/review/full-card-proposed-frames.json"],
        "recommendation": "Use lexical-v2 for fully covered compact card boundaries and readings/romaji; overlay exact-token grammar/translation fields only. User review remains required.",
    }
    report = PROJECT / "review" / "integration-report-full-card-rebuild.json"
    report.write_text(json.dumps(integration, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(combined_frames), "cards": sum(len(frame["grammarCards"]) for frame in combined_frames), "disagreements": len(disagreements), "output": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
