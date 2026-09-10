import json
import re
from pathlib import Path

from fugashi import Tagger
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
DELIVERABLES = ROOT / "deliverables"
SLUG = "mou-dou-natte-mo-ii-ya"

tagger = Tagger()
kks = kakasi()
POS_ZH = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "連体詞": "连体词", "接続詞": "连接词", "助詞": "助词", "助動詞": "助动词", "感動詞": "感叹词", "接頭辞": "前缀", "接尾辞": "后缀"}
PARTICLE_FUNCTIONS = {"は": "提示主题", "が": "标示主语／焦点", "を": "标示动作对象", "に": "标示时间、到达点或对象", "で": "标示动作场所或手段", "と": "表示并列、引用或共同对象", "も": "添加“也／都”", "の": "表示所属或名词修饰", "へ": "表示移动方向", "から": "表示起点或原因", "まで": "表示终点或范围", "より": "表示比较基准", "や": "列举事物", "ね": "寻求认同", "よ": "加强告知语气", "か": "表示疑问"}


def hira(value):
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value or "")


def romaji(value):
    return " ".join(item["hepburn"] for item in kks.convert(value)).strip()


def is_japanese(value):
    return bool(re.search(r"[ぁ-ゖァ-ヺ一-龯々ー]", value))


def token_data(surface, feature):
    pos = feature.pos1 or ""
    reading = hira(feature.kana or feature.pron or surface)
    card = {"token": surface, "reading": reading, "romaji": romaji(reading), "posZh": POS_ZH.get(pos, pos or "符号")}
    if pos == "助詞" and surface in PARTICLE_FUNCTIONS:
        card["functionZh"] = PARTICLE_FUNCTIONS[surface]
    elif re.fullmatch(r"[、。！？!?…・]+", surface):
        card["zhMeaning"] = "标点"
    else:
        card["zhMeaning"] = "词义待审核"
    return card


frames_doc = json.loads((PROJECT / "frames.review.json").read_text(encoding="utf-8"))
for frame in frames_doc["frames"]:
    sentence = frame.pop("japanese")
    source_parts = frame.pop("parts")
    frame.pop("romanizationSource", None)
    frame.pop("romanizationParts", None)
    if not is_japanese(sentence):
        frame["caption"] = {"japanese": sentence, "furigana": [], "romaji": "", "translationZh": frame.pop("translationZh", "")}
        frame["grammarCards"] = []
        frame["analysisStatus"] = "draft"
        continue
    cards = []
    furigana = []
    token_romaji = []
    cursor = 0
    for word in tagger(sentence):
        surface = word.surface
        if not surface:
            continue
        feature = word.feature
        card = token_data(surface, feature)
        cards.append(card)
        token_romaji.append(card["romaji"])
        if re.search(r"[一-龯々]", surface):
            furigana.append({"start": cursor, "length": len(surface), "text": card["reading"]})
        cursor += len(surface)
    frame["caption"] = {"japanese": sentence, "furigana": furigana, "romaji": " ".join(token_romaji), "translationZh": frame.pop("translationZh", "")}
    frame["grammarCards"] = cards
    frame["analysisStatus"] = "draft"

(PROJECT / "frames.review.json").write_text(json.dumps(frames_doc, ensure_ascii=False, indent=2), encoding="utf-8")
review = [f"# {SLUG} review", "", "状态：draft。中文释义与词卡需人工确认；视频将按当前草稿渲染。", ""]
for frame in frames_doc["frames"]:
    caption = frame["caption"]
    review += [f"## {frame['id']} · {frame['startMs'] / 1000:.2f}s", "", caption["japanese"], "", f"中文：{caption['translationZh'] or '待补充'}", ""]
    for card in frame["grammarCards"]:
        meaning = card.get("functionZh") or card.get("zhMeaning", "")
        review.append(f"- {card['token']}（{card['reading']} / {card['romaji']}）：{meaning}；{card['posZh']}")
    review.append("")
(DELIVERABLES / f"{SLUG}-review.md").write_text("\n".join(review), encoding="utf-8")
print(f"drafted {len(frames_doc['frames'])} frames and {sum(len(x['grammarCards']) for x in frames_doc['frames'])} cards")
