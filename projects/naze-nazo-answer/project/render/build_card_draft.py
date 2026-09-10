"""Create a conservative review-only Japanese card draft."""
from __future__ import annotations

import json
import re
from pathlib import Path

from janome.tokenizer import Tokenizer
from pykakasi import kakasi


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
POS = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "助詞": "助词", "助動詞": "助动词", "連体詞": "连体词", "接続詞": "连词", "感動詞": "感叹词", "代名詞": "代词"}
PARTICLES = {"は": "提示主题", "が": "提示主语", "を": "提示动作对象", "に": "提示对象／到达点", "で": "提示动作地点／手段", "と": "提示共同对象／引用内容", "の": "表示所属／修饰", "も": "表示追加／强调", "へ": "提示移动方向", "から": "表示起点／原因", "まで": "表示终点", "や": "用于不完全列举", "ね": "征求认同", "よ": "加强语气", "か": "构成疑问", "さえ": "表示极端举例／甚至", "しか": "与否定呼应，表示仅", "だけ": "限定范围"}
PUNCT = re.compile(r"^[\s、。！？!?…・「」『』（）()【】\[\]☆★—ー\-]+$")
ASCII = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,'!?-]*$")


def hira(value: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


def roman(value: str) -> str:
    return "".join(piece["hepburn"] for piece in kakasi().convert(hira(value)))


def cards_for(text: str, tokenizer: Tokenizer) -> list[dict]:
    cards = []
    for word in tokenizer.tokenize(text):
        token = word.surface
        if not token or PUNCT.match(token) or ASCII.match(token):
            continue
        feature = word.part_of_speech.split(",")
        reading = hira(word.reading if word.reading != "*" else token)
        pos = POS.get(feature[0], "其他")
        card = {"token": token, "reading": reading, "romaji": roman(reading), "grammarStructureZh": pos, "posZh": pos, "render": True, "showJlpt": False, "status": "draft", "fieldProvenance": {"token": "janome-ipadic draft", "reading": "janome-ipadic draft", "romaji": "pykakasi draft", "meaningOrFunction": "pending assisted review", "grammarStructureZh": "janome-ipadic draft"}}
        if token in PARTICLES:
            card["functionZh"] = PARTICLES[token]
        else:
            card["zhMeaning"] = "待联网核对"
        cards.append(card)
    return cards


def main() -> None:
    frames_path = PROJECT / "frames.json"
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    (PROJECT / "particle-functions.json").write_text(json.dumps(PARTICLES, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    tokenizer = Tokenizer()
    for frame in data["frames"]:
        cards = cards_for(frame["caption"]["japanese"], tokenizer)
        frame["grammarCards"] = cards
        frame["caption"]["furigana"] = []
        frame["caption"]["romaji"] = " ".join(card["romaji"] for card in cards)
        frame["status"] = "draft"
    frames_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = ["# なぜ？謎？！ANSWER｜词卡草稿", "", "整句中文来自 QQ 音乐翻译轨；自动切词、读音、罗马音与助词功能均待多角色联网审核。", ""]
    for frame in data["frames"]:
        lines += [f"## {frame['id']}  {frame['caption']['japanese']}", "", f"- 整句中文：{frame['caption'].get('translationZh') or '待人工核对'}", "- 词卡："]
        if frame["grammarCards"]:
            for card in frame["grammarCards"]:
                meaning = card.get("functionZh", card.get("zhMeaning", "待人工核对"))
                lines.append(f"  - {card['token']}｜{card['reading']}｜{card['romaji']}｜{meaning}｜{card['grammarStructureZh']}")
        else:
            lines.append("  - 无词卡（纯英文歌词）")
        lines.append("")
    out = ROOT / "deliverables" / "review" / "naze-nazo-answer-review.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(data["frames"]), "cards": sum(len(frame["grammarCards"]) for frame in data["frames"]), "review": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
