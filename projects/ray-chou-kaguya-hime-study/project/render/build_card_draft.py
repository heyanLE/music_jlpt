"""Create conservative, editable learning-card drafts without touching user captions."""
from __future__ import annotations

import json
import re
from pathlib import Path

from janome.tokenizer import Tokenizer
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
TOKENIZER, KAKASI = Tokenizer(), kakasi()
POS = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "助詞": "助词", "助動詞": "助动词", "連体詞": "连体词", "接続詞": "连词", "感動詞": "感叹词", "代名詞": "代词"}
PARTICLES = {"は": ("提示主题", "提示助词"), "が": ("提示主语", "格助词"), "を": ("标记动作对象", "格助词"), "に": ("提示对象／到达点", "格助词"), "で": ("提示动作地点／手段", "格助词"), "と": ("提示共同对象／引用", "格助词"), "の": ("表示所属／修饰", "格助词"), "も": ("表示追加／强调", "副助词"), "へ": ("提示移动方向", "格助词"), "から": ("表示起点／原因", "格助词"), "まで": ("表示终点", "副助词"), "や": ("用于不完全列举", "并列助词"), "ね": ("征求认同", "终助词"), "よ": ("加强语气", "终助词"), "か": ("构成疑问", "终助词"), "だけ": ("限定范围", "副助词")}
PUNCT = re.compile(r"^[\s、。！？!?…・「」『』（）()【】\[\]☆★—ー\-]+$")
ASCII = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,'!?\-]*$")


def hira(value: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


def romaji(value: str) -> str:
    return " ".join(piece["hepburn"] for piece in KAKASI.convert(value))


def is_kanji(char: str) -> bool:
    return "一" <= char <= "龯"


def annotations(token: str, reading: str, offset: int) -> list[dict]:
    """A conservative kanji-run reading; literal kana is never annotated."""
    output, cursor, index = [], reading, 0
    while index < len(token):
        if not is_kanji(token[index]):
            if cursor: cursor = cursor[1:]
            index += 1; continue
        end = index
        while end < len(token) and is_kanji(token[end]): end += 1
        suffix_end = end
        while suffix_end < len(token) and not is_kanji(token[suffix_end]): suffix_end += 1
        suffix = token[end:suffix_end]
        run_reading = cursor.split(suffix, 1)[0] if suffix and suffix in cursor else cursor
        if run_reading:
            output.append({"base": token[index:end], "reading": run_reading, "start": offset + index, "end": offset + end})
            cursor = cursor[len(run_reading):]
        index = end
    return output


def cards(text: str) -> tuple[list[dict], list[dict]]:
    result, ruby, cursor = [], [], 0
    for word in TOKENIZER.tokenize(text):
        token = word.surface
        position = text.find(token, cursor)
        if position >= 0: cursor = position + len(token)
        if not token or PUNCT.match(token) or ASCII.match(token): continue
        feature = word.part_of_speech.split(",")
        reading = hira(word.reading if word.reading != "*" else token)
        grammar = POS.get(feature[0], "待审词性")
        card = {"token": token, "reading": reading, "romaji": romaji(reading), "grammarStructureZh": grammar, "posZh": grammar, "status": "draft", "fieldProvenance": {"token": "janome-ipadic draft", "reading": "janome-ipadic draft", "romaji": "pykakasi draft", "meaningOrFunction": "pending assisted review", "grammarStructureZh": "janome-ipadic draft"}}
        if token in PARTICLES:
            card["functionZh"], card["grammarStructureZh"] = PARTICLES[token]
            card["posZh"] = card["grammarStructureZh"]
        else:
            card["zhMeaning"] = "待联网核对"
        result.append(card)
        if position >= 0: ruby.extend(annotations(token, reading, position))
    return result, ruby


def main() -> None:
    payload = json.loads(FRAMES.read_text(encoding="utf-8"))
    for frame in payload["frames"]:
        if frame.get("status") == "user-supplied":
            continue
        generated, ruby = cards(frame["caption"]["japanese"])
        frame["grammarCards"] = generated
        frame["caption"]["furigana"] = ruby
        frame["caption"]["romaji"] = " ".join(card["romaji"] for card in generated)
        frame["status"] = "draft"
    FRAMES.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (PROJECT / "review" / "particle-functions.json").write_text(json.dumps({"schemaVersion": 1, "functions": {key: {"functionZh": value[0], "grammarStructureZh": value[1]} for key, value in PARTICLES.items()}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    review = ["# ray（超かぐや姫！Version）｜词卡审核稿", "", "整句中文来自 QQ 音乐翻译轨；自动拆词、词性、含义和读音均待审核。两条 MV 前段台词为用户直接提供。", ""]
    for frame in payload["frames"]:
        cap = frame["caption"]; review += [f"## {frame['id']}  {frame['startMs'] / 1000:.2f}s", "", f"- 歌词：{cap['japanese']}", f"- 暂定中文：{cap.get('translationZh', '待核')}", "- 词卡："]
        if not frame["grammarCards"]: review.append("  - 无词卡（纯英文歌词）")
        for item in frame["grammarCards"]:
            meaning = item.get("functionZh", item.get("zhMeaning", "待联网核对"))
            review.append(f"  - {item['token']}｜{item['reading']}｜{item['romaji']}｜{meaning}｜{item['grammarStructureZh']}")
        review.append("")
    output = ROOT / "deliverables" / "review" / "ray-chou-kaguya-hime-study-review.md"
    output.write_text("\n".join(review), encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(payload["frames"]), "cards": sum(len(frame["grammarCards"]) for frame in payload["frames"]), "review": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
