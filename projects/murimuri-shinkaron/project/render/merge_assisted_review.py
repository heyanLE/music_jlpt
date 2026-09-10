"""Apply the user-authorized assisted-review proposal set, preserving provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT, PROPOSALS = ROOT / "project", ROOT / "project" / "proposals"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def write_review(frames: list[dict]) -> None:
    lines = ["# ムリムリ進化論｜已采纳自动审核版", "", "用户于 2026-08-22 授权整体采纳三份智能审核提案。词卡仍保留 `assisted-approved` 来源，并非人工逐卡确认。", ""]
    for frame in frames:
        cap = frame["caption"]
        lines += [f"## {frame['id']} · {frame['startMs']}–{frame['endMs']} ms", "", f"**歌词**：{cap['japanese']}", "", f"**罗马音**：{cap['romaji'] or '—'}", "", f"**中文**：{cap['translationZh']}", "", "| 分词 | 假名 | 罗马音 | 含义／功能 | 词性 |", "| --- | --- | --- | --- |"]
        for card in frame["grammarCards"]:
            meaning = card.get("zhMeaning") or card.get("functionZh")
            source_word = f"（原词：{card['sourceWord']}）" if card.get("sourceWord") else ""
            lines.append(f"| {card['token']} | {card.get('reading') or '—'} | {card.get('romaji') or '—'} | {meaning}{source_word} | {card['posZh']} |")
        lines.append("")
    out = ROOT / "deliverables" / "review" / "murimuri-shinkaron-review.md"
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    frames_path = PROJECT / "frames.json"
    before = digest(frames_path)
    data = load(frames_path)
    by_id = {frame["id"]: frame for frame in data["frames"]}
    records = []
    for name in ("assisted-review-a.json", "assisted-review-b.json", "assisted-review-c.json"):
        proposal_path = PROPOSALS / name
        proposal_data = load(proposal_path)
        for proposal in proposal_data["proposals"]:
            frame = by_id[proposal["frameId"]]
            old_translation, old_cards = frame["caption"]["translationZh"], frame["grammarCards"]
            proposed_cards = proposal.get("suggestedCards", proposal.get("newCards"))
            if proposed_cards is None:
                raise ValueError(f"Proposal has no card payload: {name} {proposal['frameId']}")
            frame["caption"]["translationZh"] = proposal["newTranslationZh"]
            frame["grammarCards"] = proposed_cards
            frame["status"] = "assisted-approved"
            provenance = frame.setdefault("fieldProvenance", {})
            provenance["translationZh"] = {"source": name, "approval": "user: 整体采纳", "confidence": proposal.get("confidence"), "evidence": proposal.get("evidence", [])}
            provenance["grammarCards"] = {"source": name, "approval": "user: 整体采纳", "changesTokenStructure": proposal.get("changesTokenStructure", False), "confidence": proposal.get("confidence"), "evidence": proposal.get("evidence", [])}
            records.append({"frameId": frame["id"], "proposal": name, "translation": {"old": old_translation, "new": proposal["newTranslationZh"]}, "cardCount": {"old": len(old_cards), "new": len(proposed_cards)}, "changesTokenStructure": proposal.get("changesTokenStructure", False), "confidence": proposal.get("confidence")})
    write_json(frames_path, data)
    after = digest(frames_path)
    write_review(data["frames"])
    write_json(PROJECT / "review" / "merge-log.json", {"schemaVersion": 1, "authorization": "user: 整体采纳", "scope": "all", "framesBeforeSha256": before, "framesAfterSha256": after, "mergedProposalFiles": ["assisted-review-a.json", "assisted-review-b.json", "assisted-review-c.json"], "records": records})
    write_json(PROJECT / "review" / "review-decision.json", {"content": "approved", "scope": "all", "renderAuthorized": False, "frameSha256": after, "authorization": "user: 整体采纳"})


if __name__ == "__main__":
    main()
