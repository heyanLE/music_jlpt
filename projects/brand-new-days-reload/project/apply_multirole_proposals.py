"""Apply the user-authorized 2026-08-15 card proposals without rendering."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "frames.reviewed.safe.json"
TARGET = ROOT / "frames.json"
PROPOSAL = ROOT / "proposals" / "multirole-cards-20260815.json"
LOG = ROOT / "review" / "merge-log-20260815.json"
REVIEW = ROOT.parent / "deliverables" / "review" / "brand-new-days-reload-review-20260815.md"
MERGE = "user-authorized-multirole-20260815"

CARD_UPDATES = {
    ("l004", "だけ"): {"functionZh": "限定范围：只／仅", "posZh": "副助词"},
    ("l004", "独り"): {"zhMeaning": "独自", "posZh": "副词"},
    ("l007", "よ"): {"functionZh": "句末告知／强调", "posZh": "终助词"},
    ("l011", "つないだ"): {"zhMeaning": "牵起的；相连的", "posZh": "动词（过去形）"},
    ("l011", "に"): {"functionZh": "受影响的原因／对象（因……而）", "posZh": "格助词"},
    ("l013", "このまま"): {"zhMeaning": "就这样", "posZh": "副词性名词"},
    ("l014", "幾つ"): {"zhMeaning": "多少个", "posZh": "疑问代词"},
    ("l014", "だろう"): {"zhMeaning": "……了多少次呢／……了吧", "posZh": "助动词"},
    ("l016", "だろう"): {"zhMeaning": "……了吧／……了吗", "posZh": "助动词"},
    ("l018", "なのに"): {"functionZh": "表示逆接：明明……却……", "posZh": "接续助词"},
    ("l030", "呼び疲れ"): {"zhMeaning": "呼喊到疲惫", "posZh": "复合动词（连用形）"},
    ("l041", "気付けば"): {"reading": "きづけば", "romaji": "kizukeba", "zhMeaning": "一留意到就；回过神来就", "posZh": "动词（ば形）"},
    ("l046", "未来"): {"reading": "あした", "romaji": "ashita", "zhMeaning": "未来", "posZh": "名词"},
}
TRANSLATIONS = {
    "l001": "唤醒梦想的晨光。", "l002": "再次照亮。", "l013": "亲爱的朋友们，就这样一直……",
    "l033": "你的笑容。", "l034": "Stay high——我都忘了呀。",
    "l036": "那一定是你给我的 true feel 的光辉。",
    "l043": "通往明日的大门，一定始终葱茏地敞开着。", "l046": "前往与你相遇的未来。"
}

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def is_kanji(ch):
    return "一" <= ch <= "龯"

def kanji_only_furigana(token, reading):
    """Return only kanji runs; existing kana stays literal and gets no ruby."""
    if not any(is_kanji(ch) for ch in token):
        return []
    chunks = re.findall(r"[一-龯]+|[^一-龯]+", token)
    cursor, result = 0, []
    for index, chunk in enumerate(chunks):
        if not is_kanji(chunk[0]):
            if reading[cursor:cursor + len(chunk)] == chunk:
                cursor += len(chunk)
            continue
        literal = chunks[index + 1] if index + 1 < len(chunks) and not is_kanji(chunks[index + 1][0]) else ""
        end = reading.find(literal, cursor) if literal else len(reading)
        if end < cursor:
            end = len(reading)
        ruby = reading[cursor:end]
        if ruby:
            result.append({"base": chunk, "reading": ruby, "romaji": ""})
        cursor = end
    return result

def caption_romaji(text, cards):
    """Preserve mixed-line source order; cards are the Japanese token source."""
    pieces, position = [], 0
    for card in cards:
        token = card["token"]
        found = text.find(token, position)
        if found < 0:
            continue
        literal = text[position:found].strip()
        if literal:
            pieces.append(literal)
        pieces.append(card["romaji"])
        position = found + len(token)
    tail = text[position:].strip()
    if tail:
        pieces.append(tail)
    return " ".join(part for part in pieces if part)

data = json.loads(SOURCE.read_text(encoding="utf-8"))
proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
operations = []
for frame in data["frames"]:
    frame_id = frame["id"]
    cards = frame["grammarCards"]
    provenance = frame.setdefault("fieldProvenance", {})
    for card in cards:
        update = CARD_UPDATES.get((frame_id, card["token"]))
        if update:
            card.update(update)
            provenance[f"card:{card['token']}"] = MERGE
            operations.append({"frameId": frame_id, "token": card["token"], "action": "update", "fields": sorted(update)})
    if frame_id == "l025":
        replacement = [
            {"token": "変えて", "reading": "かえて", "romaji": "kaete", "zhMeaning": "改变了", "posZh": "动词", "render": True},
            {"token": "しまっても", "reading": "しまっても", "romaji": "shimattemo", "functionZh": "即使彻底……了也", "posZh": "补助动词＋接续助词", "render": True}
        ]
        for index, card in enumerate(cards):
            if card["token"] == "変えてしまっても":
                cards[index:index + 1] = replacement
                provenance["card:変えてしまっても"] = MERGE
                operations.append({"frameId": frame_id, "token": "変えてしまっても", "action": "split", "into": ["変えて", "しまっても"]})
                break
        else:
            raise RuntimeError("l025 split target was not found")
    if frame_id in TRANSLATIONS:
        frame["caption"]["translationZh"] = TRANSLATIONS[frame_id]
        provenance["caption.translationZh"] = MERGE
        operations.append({"frameId": frame_id, "action": "translation"})
    furigana = []
    for card in cards:
        furigana.extend(kanji_only_furigana(card["token"], card["reading"]))
    frame["caption"]["furigana"] = furigana
    frame["caption"]["romaji"] = caption_romaji(frame["caption"]["japanese"], cards)
    provenance["caption.furigana"] = MERGE
    provenance["caption.romaji"] = MERGE
    frame["analysisStatus"] = "partially-human-confirmed"

TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
json.loads(TARGET.read_text(encoding="utf-8"))
log = {
    "schemaVersion": 1, "merge": MERGE, "authorization": "l025 拆分并采纳全部提案",
    "source": str(SOURCE), "sourceSha256": sha256(SOURCE), "proposalSha256": sha256(PROPOSAL),
    "target": str(TARGET), "targetSha256": sha256(TARGET), "operations": operations,
    "unmerged": ["No final content-review decision or render authorization was created."]
}
LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
REVIEW.parent.mkdir(parents=True, exist_ok=True)
lines = ["# Brand New Days -Reload- 词卡审核版", "", "本版已合并用户授权的多角色提案；尚未授权渲染。", ""]
for frame in data["frames"]:
    lines.extend([f"## {frame['id']}", "", f"- 日文：{frame['caption']['japanese']}", f"- 暂定中文：{frame['caption']['translationZh']}", "- 词卡："])
    for card in frame["grammarCards"]:
        meaning = card.get("functionZh", card.get("zhMeaning", ""))
        lines.append(f"  - {card['token']}（{card['romaji']}）：{meaning}｜{card['posZh']}")
    lines.append("")
REVIEW.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(json.dumps({"target": str(TARGET), "operations": len(operations), "sha256": log["targetSha256"]}, ensure_ascii=False))
