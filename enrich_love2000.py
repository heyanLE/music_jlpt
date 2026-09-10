import json
import urllib.parse
import urllib.request
from pathlib import Path

from pykakasi import kakasi
from sudachipy import dictionary, tokenizer

ROOT = Path(__file__).parent
SOURCE = ROOT / "love2000.frames.review.json"
TARGET = ROOT / "love2000.frames.annotated.review.json"
PARTICLES = json.loads((ROOT / "particle-functions.json").read_text(encoding="utf-8"))["particles"]

POS_ZH = {
    "名詞": "名词", "動詞": "动词", "形容詞": "形容词", "形状詞": "形容动词",
    "副詞": "副词", "連体詞": "连体词", "接続詞": "连词", "感動詞": "感叹词",
    "助詞": "助词", "助動詞": "助动词", "補助記号": "符号", "空白": "空白",
}
JLPT_OVERRIDES = {
    "自分": "N3", "胸": "N3", "問いかける": "N2", "愛": "N3",
    "どこ": "N5", "から": "N5", "来る": "N5", "見る": "N5",
    "今日": "N5", "人": "N5", "夢": "N4", "手": "N5", "今": "N5",
    "事": "N5", "言う": "N5", "力": "N4", "食べる": "N5", "会う": "N5",
    "あなた": "N5", "私": "N5", "胸": "N3", "興味": "N3", "風": "N4",
}

def romanize(text):
    return "".join(part["hepburn"] for part in kakasi().convert(text)).lower()

def display_romaji(surface, reading, pos):
    # Japanese particles have conventional romanizations that differ from spelling.
    if pos == "助詞" and surface == "は":
        return "wa"
    if pos == "助詞" and surface == "へ":
        return "e"
    return romanize(reading)

def to_cards(text):
    tok = dictionary.Dictionary().create()
    morphs = tok.tokenize(text, tokenizer.Tokenizer.SplitMode.C)
    cards = []
    for m in morphs:
        surface = m.surface()
        pos = m.part_of_speech()[0]
        if pos in {"空白", "補助記号"}:
            continue
        reading = m.reading_form() or surface
        card = {
            "token": surface,
            "reading": reading,
            "romaji": display_romaji(surface, reading, pos),
            "dictionaryForm": m.dictionary_form(),
            "posJa": pos,
            "posZh": POS_ZH.get(pos, "待核"),
            "zhMeaning": "待人工复核",
            "jlpt": "待人工复核",
            "reviewRequired": True,
        }
        # Keep conjugated verbs together for a card matching how learners read lyrics.
        if cards and ((pos == "助動詞" and cards[-1]["posJa"] == "動詞") or
                      (surface in {"て", "で"} and cards[-1]["posJa"] == "動詞")):
            previous = cards[-1]
            previous["token"] += card["token"]
            previous["reading"] += card["reading"]
            previous["romaji"] += card["romaji"]
            previous["dictionaryForm"] = previous["dictionaryForm"]
            previous["posZh"] = "动词（活用）"
        else:
            cards.append(card)
    return cards

def translate_ja_to_zh(text):
    query = urllib.parse.urlencode({"client": "gtx", "sl": "ja", "tl": "zh-CN", "dt": "t", "q": text})
    with urllib.request.urlopen("https://translate.googleapis.com/translate_a/single?" + query, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return "".join(piece[0] for piece in payload[0] if piece and piece[0])

project = json.loads(SOURCE.read_text(encoding="utf-8"))
frames = project["frames"]
gloss_cache = {}
for index, frame in enumerate(frames):
    frame["endMs"] = frames[index + 1]["startMs"] if index + 1 < len(frames) else project["project"]["durationMs"]
    if frame["kind"] != "lyric":
        continue
    cards = to_cards(frame["text"])
    for card in cards:
        key = card["dictionaryForm"]
        if key not in gloss_cache:
            try:
                gloss_cache[key] = translate_ja_to_zh(key)
            except Exception:
                gloss_cache[key] = "未收录"
        card["zhMeaning"] = gloss_cache[key]
        if key in JLPT_OVERRIDES:
            card["jlpt"] = JLPT_OVERRIDES[key]
        elif card["posJa"] == "助詞":
            card["jlpt"] = "N5"
        else:
            card["jlpt"] = None
        card["render"] = card["jlpt"] is not None
        card["showJlpt"] = card["jlpt"] not in {None, "N5"}
        if card["posJa"] == "助詞":
            card["functionZh"] = PARTICLES.get(card["token"], ["语法功能待核"])[0]
    frame["caption"] = {
        "japanese": frame["text"],
        "romaji": " ".join(card["romaji"] for card in cards),
        "translationZh": translate_ja_to_zh(frame["text"]),
        "furigana": [{"base": card["token"], "reading": card["reading"], "romaji": card["romaji"]} for card in cards],
    }
    frame["grammarCards"] = cards
    frame["analysisStatus"] = "auto-draft-needs-linguistic-review"

project["reviewStatus"] = "content-complete-auto-draft-needs-linguistic-review"
project["reviewNotes"] = [
    "读音、词性和罗马音由 Sudachi + pykakasi 自动生成。",
    "中文释义、JLPT 和中文整句翻译必须经人工或受控词典复核后才能进入最终渲染。",
    "歌词中的省略、口语、片假名表记和英语夹杂可能需要合并或改写分词卡片。",
]
TARGET.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(TARGET)
