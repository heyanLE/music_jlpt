"""Create a conservative, review-only Japanese token/card draft."""
from __future__ import annotations

import json
import re
from pathlib import Path

from janome.tokenizer import Tokenizer
from pykakasi import kakasi


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
PARTICLES = PROJECT / "particle-functions.json"
REVIEW = ROOT / "deliverables" / "review" / "dare-ni-mo-narenai-watashi-dakara-v3-review.md"

POS = {
    "名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词",
    "助詞": "助词", "助動詞": "助动词", "連体詞": "连体词", "接続詞": "连词",
    "感動詞": "感叹词", "代名詞": "代词", "記号": "符号",
}
PARTICLE_FUNCTIONS = {
    "は": "提示主题", "が": "提示主语", "を": "提示动作对象", "に": "提示对象／到达点",
    "で": "提示动作地点／手段", "と": "提示共同对象／引用内容", "の": "表示所属／修饰",
    "も": "表示追加／强调", "へ": "提示移动方向", "から": "表示起点／原因", "まで": "表示终点",
    "や": "用于不完全列举", "ね": "征求认同", "よ": "加强语气", "か": "构成疑问",
    "しか": "与否定呼应，表示仅", "だけ": "限定范围", "ばかり": "表示净是／只顾",
}
PUNCTUATION = re.compile(r"^[\s、。！？!?…・「」『』（）()【】\[\]—ー\-]+$")


def hira(value: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


def romaji(value: str) -> str:
    return "".join(item["hepburn"] for item in kakasi().convert(hira(value)))


def is_english(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value)) and all(char.isascii() or char.isspace() or char in "-'!?.," for char in value)


def build_cards(text: str, tagger: Tokenizer) -> list[dict]:
    if is_english(text):
        return []
    cards = []
    for word in tagger.tokenize(text):
        token = word.surface
        if not token or PUNCTUATION.match(token) or is_english(token):
            continue
        feature = word.part_of_speech.split(",")
        reading = hira(word.reading if word.reading != "*" else token)
        pos = POS.get(feature[0], "其他")
        card = {
            "token": token,
            "reading": reading,
            "romaji": romaji(reading),
            "grammarStructureZh": pos,
            "posZh": pos,
            "render": True,
            "showJlpt": False,
            "status": "draft",
            "fieldProvenance": {
                "token": "janome-ipadic draft",
                "reading": "janome-ipadic draft",
                "romaji": "pykakasi draft",
                "meaningOrFunction": "pending assisted review",
                "grammarStructureZh": "janome-ipadic draft",
            },
        }
        if token in PARTICLE_FUNCTIONS:
            card["functionZh"] = PARTICLE_FUNCTIONS[token]
        else:
            card["zhMeaning"] = "待联网核对"
        cards.append(card)
    return cards


def main() -> None:
    data = json.loads(FRAMES.read_text(encoding="utf-8"))
    PARTICLES.write_text(json.dumps(PARTICLE_FUNCTIONS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    tagger = Tokenizer()
    for frame in data["frames"]:
        text = frame["caption"]["japanese"]
        cards = build_cards(text, tagger)
        frame["grammarCards"] = cards
        frame["caption"]["furigana"] = []
        if cards:
            frame["caption"]["romaji"] = " ".join(card["romaji"] for card in cards)
        frame["status"] = "draft"

    FRAMES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = [
        "# 誰にもなれない私だから｜词卡草稿",
        "",
        "本稿仅完成自动切词、读音、罗马音与助词功能。整句中文来自 QQ 音乐翻译轨；其他词义均待多角色联网审核。",
        "",
    ]
    for frame in data["frames"]:
        caption = frame["caption"]
        lines.extend([f"## {frame['id']}  {caption['japanese']}", "", f"- 整句中文：{caption.get('translationZh') or '待人工核对'}", "- 词卡："])
        for card in frame["grammarCards"]:
            meaning = card.get("functionZh") or card.get("zhMeaning", "待人工核对")
            lines.append(f"  - {card['token']}｜{card['reading']}｜{card['romaji']}｜{meaning}｜{card['grammarStructureZh']}")
        if not frame["grammarCards"]:
            lines.append("  - 无词卡（纯英文歌词）")
        lines.append("")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(data["frames"]), "cards": sum(len(frame["grammarCards"]) for frame in data["frames"]), "review": str(REVIEW)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
