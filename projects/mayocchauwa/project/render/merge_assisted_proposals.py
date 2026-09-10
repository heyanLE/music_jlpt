"""Merge explicitly approved assisted proposals; refuse stale or human-confirmed frames."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frame_path = PROJECT / "frames.json"
    doc = load(frame_path)
    frames = {frame["id"]: frame for frame in doc["frames"]}
    proposals = []
    for path in sorted((PROJECT / "proposals").glob("assisted-review-*.json")):
        proposals.extend(load(path)["proposals"])
    if len(proposals) != 63 or len({item["frameId"] for item in proposals}) != 63:
        raise RuntimeError("Expected one proposal for each of 63 frames")
    merged = []
    for item in proposals:
        frame = frames[item["frameId"]]
        if frame.get("status") == "human-confirmed":
            raise RuntimeError(f"Refusing to overwrite human-confirmed {frame['id']}")
        old = item["oldCaption"]
        if isinstance(old, str):
            if frame["caption"].get("japanese") != old:
                raise RuntimeError(f"Stale proposal {frame['id']} caption.japanese")
        else:
            for field in ("japanese", "romaji", "translationZh"):
                if frame["caption"].get(field) != old.get(field):
                    raise RuntimeError(f"Stale proposal {frame['id']} caption.{field}")
        previous = {"translationZh": frame["caption"]["translationZh"], "grammarCards": frame["grammarCards"]}
        frame["caption"]["translationZh"] = item["newTranslationZh"]
        frame["caption"]["translationStatus"] = "assisted-reviewed; user-approved"
        cards = []
        annotations = []
        for card in item["suggestedCards"]:
            card = dict(card)
            card["status"] = "assisted-reviewed; user-approved"
            card["fieldProvenance"] = "assisted proposal; user approved overall"
            cards.append(card)
            annotations.extend(DRAFT.kanji_annotations(card["token"], card["reading"]))
        frame["caption"]["furigana"] = annotations
        frame["grammarCards"] = cards
        frame["status"] = "human-confirmed"
        frame.setdefault("fieldProvenance", {})["approvedMerge"] = "project/proposals/assisted-review-[a-c].json"
        merged.append({"frameId": frame["id"], "old": previous, "new": {"translationZh": item["newTranslationZh"], "grammarCards": cards}, "confidence": item["confidence"], "evidence": item["evidence"], "changesTokenStructure": item["changesTokenStructure"]})
    write(frame_path, doc)
    review = ["# 迷っちゃうわ｜已采纳词卡审核稿", "", "本稿已按用户“整体采纳”合并三组多角色审核提案。词卡、句译与分词均可继续修订；尚未授权最终渲染。", ""]
    for frame in doc["frames"]:
        cap = frame["caption"]
        review += [f"## {frame['id']}　{frame['startMs']/1000:06.2f}", f"歌词：{cap['japanese']}", f"中文：{cap['translationZh']}", "", "词卡："]
        if not frame["grammarCards"]:
            review.append("- 纯英文行：不显示假名、罗马音或词卡。")
        for card in frame["grammarCards"]:
            meaning = card.get("functionZh", card.get("zhMeaning", ""))
            source = f"｜原词：{card['sourceWord']}" if card.get("sourceWord") else ""
            review += [f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}{source}", f"  - 含义／功能：{meaning}", f"  - 词性：{card['posZh']}"]
        review.append("")
    (ROOT / "deliverables" / "review" / "mayocchauwa-review.md").write_text("\n".join(review), encoding="utf-8", newline="\n")
    layout = DRAFT.render_preview(doc["frames"])
    write(PROJECT / "qa" / "layout-report.json", {"schemaVersion": 1, "result": "passed" if not layout["failures"] else "failed", "preview": layout["preview"], "representative": {"maximumCards": layout["sample"], "maximumCardCount": layout["cardCount"]}, "cardCheck": {"meaningMaxLines": 2, "tokenAndPosOneLine": True, "overflowTokens": layout["failures"]}, "source": "user-approved assisted proposal merge"})
    write(PROJECT / "review" / "merge-log.json", {"schemaVersion": 1, "decision": "整体采纳", "scope": "all", "proposalFiles": ["project/proposals/assisted-review-a.json", "project/proposals/assisted-review-b.json", "project/proposals/assisted-review-c.json"], "merged": merged, "framesSha256": sha(frame_path)})
    write(PROJECT / "review" / "review-decision.json", {"content": "approved", "scope": "all", "renderAuthorized": False, "userWording": "整体采纳", "frameSha256": sha(frame_path)})


spec = importlib.util.spec_from_file_location("draft", PROJECT / "render" / "build_card_draft.py")
DRAFT = importlib.util.module_from_spec(spec)
spec.loader.exec_module(DRAFT)

if __name__ == "__main__":
    main()
