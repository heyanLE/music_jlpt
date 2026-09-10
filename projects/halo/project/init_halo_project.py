"""Create the review-first HALO learning-video project from archived QQ Music assets."""
import json
import re
from pathlib import Path

from pykakasi import kakasi
from sudachipy import dictionary, tokenizer


ROOT = Path(__file__).parent
ARCHIVE = ROOT.parent
SOURCE = ARCHIVE / "source"
DELIVERABLES = ARCHIVE / "deliverables"
QM = json.loads((DELIVERABLES / "halo-qm.parsed.json").read_text(encoding="utf-8"))["content"]
QMTS = (DELIVERABLES / "halo-qmts.xml").read_text(encoding="utf-8")
PARTICLES = {
    "は": "主题提示", "が": "主语标记", "を": "直接宾语标记", "に": "动作对象、到达点",
    "で": "动作、状态发生的地点", "と": "共同对象、引用", "の": "所属修饰",
    "も": "添加、并列", "へ": "方向", "から": "起点、来源", "まで": "终点、范围",
    "や": "不完全列举", "ね": "征求认同、加强感叹", "よ": "告知、强调",
}
POS = {
    "名詞": "名词", "代名詞": "人称代词", "動詞": "动词", "形容詞": "形容词",
    "形状詞": "形容动词", "副詞": "副词", "連体詞": "连体词", "接続詞": "连词",
    "助詞": "助词", "助動詞": "助动词", "感動詞": "感叹词",
}


def roma(value):
    return "".join(item["hepburn"] for item in kakasi().convert(value)).lower()


def make_cards(text):
    cards = []
    for token in dictionary.Dictionary().create().tokenize(text, tokenizer.Tokenizer.SplitMode.C):
        surface, pos = token.surface(), token.part_of_speech()[0]
        if pos in {"空白", "補助記号"}:
            continue
        reading = token.reading_form() or surface
        value = {
            "token": surface, "reading": reading,
            "romaji": "wa" if surface == "は" and pos == "助詞" else roma(reading),
            "dictionaryForm": token.dictionary_form(), "posJa": pos,
            "posZh": POS.get(pos, "待核"), "zhMeaning": "待人工审核",
            "reviewRequired": True, "render": True, "showJlpt": False,
        }
        if pos == "助詞":
            value["functionZh"] = PARTICLES.get(surface, "语法功能待核")
        # Keep spoken conjugation chunks together for learner-facing cards.
        if cards and ((pos == "助動詞" and cards[-1]["posJa"] == "動詞") or (surface in {"て", "た", "ない"} and cards[-1]["posJa"] == "動詞")):
            cards[-1]["token"] += surface
            cards[-1]["reading"] += reading
            cards[-1]["romaji"] += value["romaji"]
            cards[-1]["posZh"] = "动词（活用）"
        else:
            cards.append(value)
    return cards


translations = []
for minute, second, value in re.findall(r"^\[(\d{2}):(\d{2}\.\d{2})\](.*)$", QMTS, re.M):
    value = value.strip()
    if value and not value.startswith(("//", "TME")):
        translations.append((int(minute) * 60000 + round(float(second) * 1000), value))

frames = []
for line in QM:
    text = "".join(item["content"] for item in line["content"]).strip()
    start, end = line["start"], line["start"] + line["duration"]
    # Skip title/credit metadata, retaining the song's actual Japanese lyric timeline.
    if start < 634 or not re.search(r"[ぁ-んァ-ヶ一-龯]", text):
        continue
    cards = make_cards(text)
    nearby = [value for timestamp, value in translations if start - 80 <= timestamp < end - 80]
    frame = {
        "id": f"l{len(frames) + 1:03d}", "kind": "lyric", "startMs": start, "endMs": end,
        "caption": {
            "japanese": text, "romaji": " ".join(card["romaji"] for card in cards),
            "translationZh": "，".join(nearby) or "待人工审核",
            "furigana": [{"base": card["token"], "reading": card["reading"], "romaji": card["romaji"]} for card in cards],
        },
        "grammarCards": cards, "analysisStatus": "auto-draft-needs-human-review", "reviewRequired": True,
    }
    frames.append(frame)

project = {
    "schemaVersion": "1.0",
    "project": {
        "id": "halo-nomelon-nolemon", "title": "HALO", "artist": "NOMELON NOLEMON",
        "audio": str(SOURCE / "HALO.flac"), "backgroundVideo": str(next(SOURCE.glob("*.mp4"))),
        "cover": str(SOURCE / "COVER.jpg"), "durationMs": 186000, "canvas": {"width": 1920, "height": 1080},
    },
    "wordTimingSource": {"format": "QQ Music QRC", "parsedTimeline": str(DELIVERABLES / "halo-qm.parsed.json"), "romajiSource": str(DELIVERABLES / "halo-qmRoma.parsed.json"), "translationSource": str(DELIVERABLES / "halo-qmts.xml")},
    "reviewStatus": "auto-draft-needs-human-review", "frames": frames,
}
(ROOT / "halo.frames.review.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

lines = ["# HALO｜逐句词卡审核", "", "已接入 QQ Music 日文、逐字时序、罗马音与中文翻译轨。请直接修改暂定中文、词卡含义或词性；确认后回复“核对完了”。", ""]
for frame in frames:
    caption = frame["caption"]
    lines += [f"## {frame['id']} · {frame['startMs'] / 1000:.3f}s", "", f"日文：{caption['japanese']}", f"暂定中文：{caption['translationZh']}", "", "待核词卡："]
    for card in frame["grammarCards"]:
        lines += [f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}", f"  - 暂定：{card.get('functionZh', card['zhMeaning'])}", f"  - 词性：{card['posZh']}"]
    lines.append("")
(DELIVERABLES / "halo-review.md").write_text("\n".join(lines), encoding="utf-8")
print(f"frames={len(frames)}")
