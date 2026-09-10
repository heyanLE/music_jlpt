#!/usr/bin/env python3
"""Integrate three role proposals without modifying project/frames.json."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
FRAMES_PATH = PROJECT / "frames.json"
PROPOSALS = PROJECT / "proposals"
REPORT = PROJECT / "review" / "integration-report.json"
REVIEW = ROOT / "deliverables" / "review" / "mebuku-toki-assisted-review.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


FIELD_RE = re.compile(r"^grammarCards\[(\d+)\]\.(zhMeaning|functionZh)$")


def field_value(frame: dict, field: str):
    if field == "grammarCards":
        return frame["grammarCards"]
    if field.startswith("caption."):
        return frame["caption"].get(field.split(".", 1)[1])
    match = FIELD_RE.match(field)
    if match:
        return frame["grammarCards"][int(match.group(1))].get(match.group(2))
    raise ValueError(f"Unsupported proposal field: {field}")


SPECIAL: dict[tuple[str, str, int], dict] = {
    ("l001", "めいっぱい", 0): {"zhMeaning": "竭尽全力", "grammarStructureZh": "副词（程度）"},
    ("l001", "してきた", 0): {"zhMeaning": "一路……至今", "grammarStructureZh": "Vてくる（过去至今）"},
    ("l002", "できない", 0): {"zhMeaning": "做不好", "grammarStructureZh": "动词可能否定形"},
    ("l004", "変わっていく", 0): {"zhMeaning": "逐渐变化下去", "grammarStructureZh": "Vていく（变化持续）"},
    ("l005", "気づいてない", 0): {"zhMeaning": "还没察觉", "grammarStructureZh": "Vていない（口语省略）"},
    ("l006", "望んだ", 0): {"zhMeaning": "曾经向往的", "grammarStructureZh": "动词过去形"},
    ("l006", "とは", 0): {"functionZh": "提示比较对象并形成对照", "grammarStructureZh": "格助词＋提示助词"},
    ("l008", "なにも", 0): {"functionZh": "与否定呼应：什么都……", "grammarStructureZh": "疑问代词＋副助词"},
    ("l008", "いらない", 0): {"zhMeaning": "不需要", "grammarStructureZh": "动词否定形"},
    ("l009", "いて", 0): {"zhMeaning": "待在；在", "grammarStructureZh": "动词て形（请求）"},
    ("l010", "な", 0): {"functionZh": "表达愿望语气", "grammarStructureZh": "终助词"},
    ("l010", "が", 0): {"functionZh": "提示从句主语", "grammarStructureZh": "格助词"},
    ("l010", "が", 1): {"functionZh": "愿望评价对象", "grammarStructureZh": "格助词"},
    ("l010", "って", 0): {"functionZh": "引用愿望内容", "grammarStructureZh": "引用助词"},
    ("l011", "思っていたって", 0): {"functionZh": "即使一直这么想", "grammarStructureZh": "V过去＋たって（让步）"},
    ("l011", "変えられない", 0): {"zhMeaning": "无法改变", "grammarStructureZh": "动词可能否定形"},
    ("l012", "伝えなくちゃ", 0): {"functionZh": "必须传达（省略「ならない」）", "grammarStructureZh": "Vなくちゃ（义务・口语）"},
    ("l013", "できない", 0): {"zhMeaning": "做不到", "grammarStructureZh": "动词可能否定形"},
    ("l013", "目を向けて", 0): {"zhMeaning": "把目光投向", "grammarStructureZh": "固定搭配＋て形"},
    ("l014", "教えたい", 0): {"zhMeaning": "想告诉", "grammarStructureZh": "Vたい（愿望）"},
    ("l015", "知りたい", 0): {"zhMeaning": "想了解", "grammarStructureZh": "Vたい（愿望）"},
    ("l015", "で", 0): {"functionZh": "断定并承接下文", "grammarStructureZh": "助动词「だ」连用形"},
    ("l017", "わけじゃない", 0): {"functionZh": "并不是……", "grammarStructureZh": "わけではない（口语）"},
    ("l018", "気づいてない", 0): {"zhMeaning": "还没察觉", "grammarStructureZh": "Vていない（口语省略）"},
    ("l018", "んだ", 0): {"functionZh": "补充说明语气", "grammarStructureZh": "のだ（口语）"},
    ("l020", "ためらわないで", 0): {"functionZh": "请不要犹豫", "grammarStructureZh": "Vないで（否定请求）"},
    ("l021", "今まで", 0): {"zhMeaning": "迄今为止", "grammarStructureZh": "时间副词"},
    ("l023", "望んだ", 0): {"zhMeaning": "曾经向往的", "grammarStructureZh": "动词过去形"},
    ("l023", "とは", 0): {"functionZh": "提示比较对象并形成对照", "grammarStructureZh": "格助词＋提示助词"},
    ("l025", "なにも", 0): {"functionZh": "与否定呼应：什么都……", "grammarStructureZh": "疑问代词＋副助词"},
    ("l025", "いらない", 0): {"zhMeaning": "不需要", "grammarStructureZh": "动词否定形"},
    ("l026", "いて", 0): {"zhMeaning": "待在；在", "grammarStructureZh": "动词て形（请求）"},
    ("l027", "で", 0): {"functionZh": "表示状态并连接后项", "grammarStructureZh": "ナ形容词＋で（中顿）"},
    ("l027", "すれ違って", 0): {"zhMeaning": "错过彼此；产生隔阂", "grammarStructureZh": "动词て形"},
    ("l028", "勘繰って", 0): {"zhMeaning": "胡乱猜忌", "grammarStructureZh": "动词て形"},
    ("l028", "僕たち", 0): {"zhMeaning": "我们", "grammarStructureZh": "代词＋复数后缀"},
    ("l029", "言えない", 0): {"zhMeaning": "说不出口", "grammarStructureZh": "动词可能否定形"},
    ("l029", "言えない", 1): {"zhMeaning": "说不出口", "grammarStructureZh": "动词可能否定形"},
    ("l029", "なんて", 0): {"zhMeaning": "多么；何等", "grammarStructureZh": "副词（感叹程度）"},
    ("l030", "なんだろう", 0): {"functionZh": "说明并推测：大概……吧", "grammarStructureZh": "のだろう（说明・推量）"},
    ("l031", "な", 0): {"functionZh": "表达愿望语气", "grammarStructureZh": "终助词"},
    ("l031", "が", 0): {"functionZh": "提示从句主语", "grammarStructureZh": "格助词"},
    ("l031", "が", 1): {"functionZh": "愿望评价对象", "grammarStructureZh": "格助词"},
    ("l031", "って", 0): {"functionZh": "引用愿望内容", "grammarStructureZh": "引用助词"},
    ("l032", "思っていたって", 0): {"functionZh": "即使一直这么想", "grammarStructureZh": "V过去＋たって（让步）"},
    ("l032", "変えられない", 0): {"zhMeaning": "无法改变", "grammarStructureZh": "动词可能否定形"},
    ("l033", "伝えなくちゃ", 0): {"functionZh": "必须传达（省略「ならない」）", "grammarStructureZh": "Vなくちゃ（义务・口语）"},
}

LINE_OVERRIDES = {
    "l029": "嘴上总说着“说不出口、说不出口”",
    "l030": "我们是多么任性啊",
}


def translated_old_cards(frame: dict, translation: dict) -> list[dict]:
    cards = copy.deepcopy(frame["grammarCards"])
    for change in translation["changes"]:
        if change["frameId"] != frame["id"]:
            continue
        match = FIELD_RE.match(change["field"])
        if not match:
            continue
        index, key = int(match.group(1)), match.group(2)
        if change["new"] is None:
            cards[index].pop(key, None)
        else:
            cards[index][key] = change["new"]
    return cards


def card_spans(cards: list[dict]) -> list[tuple[int, int]]:
    spans, cursor = [], 0
    for card in cards:
        end = cursor + len(card["token"])
        spans.append((cursor, end))
        cursor = end
    return spans


def exact_grammar_cards(grammar_change: dict | None) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    if grammar_change:
        for card in grammar_change["new"]:
            result.setdefault(card["token"], []).append(card)
    return result


def semantic_from_old(target_span: tuple[int, int], old_cards: list[dict], old_spans: list[tuple[int, int]]) -> dict | None:
    indices = [index for index, span in enumerate(old_spans) if span == target_span]
    if len(indices) != 1:
        return None
    source = old_cards[indices[0]]
    if source.get("functionZh"):
        return {"functionZh": source["functionZh"]}
    if source.get("zhMeaning") and source["zhMeaning"] != "待联网核对":
        return {"zhMeaning": source["zhMeaning"]}
    return None


def main() -> None:
    frames_doc = load(FRAMES_PATH)
    frames = {frame["id"]: frame for frame in frames_doc["frames"]}
    base_sha = sha(FRAMES_PATH)
    proposals = {role: load(PROPOSALS / f"{role}.json") for role in ("lexical", "grammar", "translation")}
    for role, document in proposals.items():
        if document.get("baseFrameSha256") != base_sha:
            raise SystemExit(f"Stale {role} proposal")
        for change in document["changes"]:
            if field_value(frames[change["frameId"]], change["field"]) != change["old"]:
                raise SystemExit(f"Old-value mismatch: {role} {change['frameId']} {change['field']}")

    lexical_by_frame = {(change["frameId"], change["field"]): change for change in proposals["lexical"]["changes"]}
    grammar_by_frame = {change["frameId"]: change for change in proposals["grammar"]["changes"] if change["field"] == "grammarCards"}
    translation_by_frame = {(change["frameId"], change["field"]): change for change in proposals["translation"]["changes"]}

    recommended = []
    attention = []
    for frame_id, frame in frames.items():
        lexical_change = lexical_by_frame.get((frame_id, "grammarCards"))
        target_cards = copy.deepcopy(lexical_change["new"] if lexical_change else frame["grammarCards"])
        old_semantic_cards = translated_old_cards(frame, proposals["translation"])
        old_spans, target_spans = card_spans(frame["grammarCards"]), card_spans(target_cards)
        if old_spans and target_spans and old_spans[-1][1] != target_spans[-1][1]:
            raise SystemExit(f"Token coverage mismatch: {frame_id}")
        grammar_exact = exact_grammar_cards(grammar_by_frame.get(frame_id))
        token_occurrence: dict[str, int] = {}
        final_cards = []
        for index, card in enumerate(target_cards):
            token = card["token"]
            occurrence = token_occurrence.get(token, 0)
            token_occurrence[token] = occurrence + 1
            result = copy.deepcopy(card)
            result.pop("zhMeaning", None)
            result.pop("functionZh", None)
            semantic = semantic_from_old(target_spans[index], old_semantic_cards, old_spans)
            if semantic:
                result.update(semantic)
            grammar_candidates = grammar_exact.get(token, [])
            if occurrence < len(grammar_candidates):
                candidate = grammar_candidates[occurrence]
                if candidate.get("grammarStructureZh"):
                    result["grammarStructureZh"] = candidate["grammarStructureZh"]
                if candidate.get("functionZh"):
                    result.pop("zhMeaning", None)
                    result["functionZh"] = candidate["functionZh"]
            special = SPECIAL.get((frame_id, token, occurrence))
            if special:
                result.pop("zhMeaning", None)
                result.pop("functionZh", None)
                result.update(special)
            if bool(result.get("zhMeaning")) == bool(result.get("functionZh")):
                raise SystemExit(f"Unresolved semantic field: {frame_id} {token}#{occurrence}")
            if not result.get("grammarStructureZh"):
                raise SystemExit(f"Missing grammar structure: {frame_id} {token}#{occurrence}")
            result["status"] = "assisted-proposal"
            result["fieldProvenance"] = {
                "tokenReadingRomaji": "lexical role proposal or unchanged draft",
                "meaningOrFunction": "translation role proposal with integration remap",
                "grammarStructureZh": "grammar role proposal with lexical-boundary integration",
            }
            final_cards.append(result)
        if final_cards != frame["grammarCards"]:
            recommended.append({
                "frameId": frame_id,
                "field": "grammarCards",
                "old": frame["grammarCards"],
                "new": final_cards,
                "confidence": 0.95,
                "evidence": ["integrated lexical, grammar, and translation role proposals", "lexical token boundaries preserved; semantic proposals remapped by token span"],
                "changesTokenStructure": bool(lexical_change),
            })
        for field in ("caption.furigana", "caption.romaji"):
            change = lexical_by_frame.get((frame_id, field))
            if change:
                recommended.append(copy.deepcopy(change))
        translation_change = translation_by_frame.get((frame_id, "caption.translationZh"))
        line_new = LINE_OVERRIDES.get(frame_id, translation_change["new"] if translation_change else frame["caption"]["translationZh"])
        if line_new != frame["caption"]["translationZh"]:
            recommended.append({
                "frameId": frame_id,
                "field": "caption.translationZh",
                "old": frame["caption"]["translationZh"],
                "new": line_new,
                "confidence": 0.97,
                "evidence": ["translation role cross-line review", "grammar role precedence for l029-l030 cross-line なんて勝手なんだろう"],
                "changesTokenStructure": False,
            })

    attention.extend([
        {"frameIds": ["l004", "l005"], "issue": "QQ translation rows were semantically reversed", "recommendation": "l004=这份不断变化着的心情；l005=连我自己都还没有察觉"},
        {"frameIds": ["l010", "l031"], "issue": "明日 has multiple normal readings", "recommendation": "Use singing-track reading あす / asu"},
        {"frameIds": ["l015", "l027"], "issue": "で was drafted as a generic particle", "recommendation": "Treat as copular/adjectival continuative で, not location/instrument"},
        {"frameIds": ["l029", "l030"], "issue": "Translation and grammar roles disagreed on なんて", "recommendation": "Use adverbial exclamation 多么／何等 in cross-line なんて勝手なんだろう"},
        {"frameIds": ["l034"], "issue": "Final lyric is a deliberately fragmentary reprise", "recommendation": "Keep 最初に／最後は as separate cards and provisional translation 最初时／最后则……"},
    ])

    report = {
        "schemaVersion": 2,
        "reviewRole": "integration",
        "status": "completed",
        "baseFrameSha256": base_sha,
        "sourceProposalFiles": [f"project/proposals/{role}.json" for role in ("lexical", "grammar", "translation")],
        "proposalCounts": {role: len(document["changes"]) for role, document in proposals.items()},
        "conflicts": [
            {"scope": "all grammarCards", "roles": ["lexical", "grammar", "translation"], "resolution": "Lexical role owns token boundaries; grammar and translation fields are remapped onto those boundaries."},
            {"scope": ["l010", "l031"], "roles": ["lexical", "grammar"], "resolution": "Use あす from frozen singing track; reject generic あした."},
            {"scope": ["l029", "l030"], "roles": ["grammar", "translation"], "resolution": "Use cross-line adverbial-exclamation analysis for なんて勝手なんだろう and adjust both Chinese lines."},
        ],
        "recommendedProposalSet": {
            "strategy": "apply integrated whole-card arrays first, then caption furigana/romaji/translation changes",
            "changes": recommended,
        },
        "attentionItems": attention,
        "protectedHumanFieldsTouched": [],
        "framesModified": False,
    }
    write(REPORT, report)

    recommendations_by_frame: dict[str, dict[str, dict]] = {}
    for change in recommended:
        recommendations_by_frame.setdefault(change["frameId"], {})[change["field"]] = change
    lines = [
        "# 芽吹くとき｜多角色整合审阅稿",
        "",
        "本稿是词法、文法与翻译三角色的整合提案，尚未写入 frames.json，也不代表人工确认。",
        "",
        "## 暂定整句中文",
        "",
    ]
    for frame_id, frame in frames.items():
        line_change = recommendations_by_frame.get(frame_id, {}).get("caption.translationZh")
        line_value = line_change["new"] if line_change else frame["caption"]["translationZh"]
        lines.append(f"- **{frame_id}**　{frame['caption']['japanese']} → {line_value}")
    lines.extend(["", "## 需要重点确认的词卡／判断", ""])
    for item in attention:
        lines.append(f"- **{', '.join(item['frameIds'])}**：{item['issue']}；建议：{item['recommendation']}。")
    lines.extend(["", "## 重点帧的整合词卡", ""])
    for frame_id in ("l001", "l004", "l005", "l010", "l011", "l012", "l015", "l027", "l028", "l029", "l030", "l034"):
        card_change = recommendations_by_frame[frame_id]["grammarCards"]
        lines.append(f"### {frame_id}　{frames[frame_id]['caption']['japanese']}")
        for card in card_change["new"]:
            semantic = card.get("functionZh") or card.get("zhMeaning")
            source = f"｜词源 {card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}｜{semantic}｜{card['grammarStructureZh']}{source}")
        lines.append("")
    REVIEW.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"integration": str(REPORT), "review": str(REVIEW), "recommendedChanges": len(recommended), "attentionItems": len(attention)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
