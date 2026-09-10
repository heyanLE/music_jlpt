#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

from janome.tokenizer import Tokenizer
from pykakasi import kakasi


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES_PATH = PROJECT / "frames.json"
REVIEW_PATH = ROOT / "deliverables" / "review" / "heavenly-me-study-review.md"
PARTICLE_PATH = PROJECT / "review" / "particle-function-table.json"

TOKENIZER = Tokenizer()
KAKASI = kakasi()


def item(token: str, value: str, grammar: str, *, function: bool = False, source_word: str | None = None) -> dict:
    result = {"token": token, "grammarStructureZh": grammar}
    result["functionZh" if function else "zhMeaning"] = value
    if source_word:
        result["sourceWord"] = source_word
    return result


CARD_SPECS: dict[str, list[dict]] = {
    "自由に羽ばたいて": [
        item("自由", "自由；不受束缚", "名词／ナ形容词词干"),
        item("に", "表示动作状态：自由地", "格助词", function=True),
        item("羽ばたいて", "振翅飞翔", "动词て形"),
    ],
    "この希望を装填して": [
        item("この", "这个", "连体词"), item("希望", "希望", "名词"),
        item("を", "标示动作对象", "格助词", function=True),
        item("装填して", "装填；装入", "サ变动词て形"),
    ],
    "大丈夫このまま": [
        item("大丈夫", "没关系；不要紧", "ナ形容词词干"),
        item("このまま", "就这样；保持现状", "固定表达"),
    ],
    "さぁ あたしの手を取って": [
        item("さぁ", "来吧", "感叹词"), item("あたし", "我（女性口语）", "人称代词"),
        item("の", "表示所属", "格助词", function=True), item("手", "手", "名词"),
        item("を", "标示动作对象", "格助词", function=True), item("取って", "握住；牵起", "动词て形"),
    ],
    "今日という日を祝って笑って愛して": [
        item("今日", "今天", "名词"), item("という", "称为；所谓", "引用＋言う"),
        item("日", "日子", "名词"), item("を", "标示动作对象", "格助词", function=True),
        item("祝って", "庆祝", "动词て形"), item("笑って", "欢笑", "动词て形"),
        item("愛して", "去爱；热爱", "动词て形"),
    ],
    "光になるから 鼓動を鳴らして": [
        item("光", "光芒", "名词"), item("に", "标示变化后的结果", "格助词", function=True),
        item("なる", "变成", "动词"), item("から", "表示原因：因为", "接续助词", function=True),
        item("鼓動", "心跳；搏动", "名词"), item("を", "标示动作对象", "格助词", function=True),
        item("鳴らして", "使……鸣响", "他动词て形"),
    ],
    "消えない傷を抱えていても": [
        item("消えない", "不会消失的", "动词ない形"), item("傷", "伤痕", "名词"),
        item("を", "标示动作对象", "格助词", function=True),
        item("抱えていても", "即使一直怀抱着", "Vている＋ても（让步）"),
    ],
    "眠れないほどに悔やんでいても": [
        item("眠れない", "无法入睡", "可能动词否定形"),
        item("ほどに", "达到……的程度", "程度助词＋格助词", function=True),
        item("悔やんでいても", "即使一直懊悔", "Vている＋ても（让步）"),
    ],
    "君に似合う笑顔を探す": [
        item("君", "你", "人称代词"), item("に", "标示适合的对象", "格助词", function=True),
        item("似合う", "适合；相配", "动词"), item("笑顔", "笑容", "名词"),
        item("を", "标示动作对象", "格助词", function=True), item("探す", "寻找", "动词"),
    ],
    "期待していてよ": [
        item("期待していて", "期待着吧", "Vている＋て（请求）"),
        item("よ", "加强告知或劝说语气", "终助词", function=True),
    ],
    "飛び立つ空に祈り撃ち放て": [
        item("飛び立つ", "起飞；展翅飞去", "复合动词"), item("空", "天空", "名词"),
        item("に", "标示动作方向", "格助词", function=True), item("祈り", "祈祷；愿望", "名词"),
        item("撃ち放て", "发射出去", "复合动词命令形"),
    ],
    "目覚めた命 今を生きるんだ": [
        item("目覚めた", "苏醒的", "动词た形（连体）"), item("命", "生命", "名词"),
        item("今", "当下；现在", "名词"), item("を", "标示经历的时空", "格助词", function=True),
        item("生きるんだ", "就是活在当下", "Vる＋のだ（说明强调）"),
    ],
    "守れるものはこの瞬間だけ": [
        item("守れる", "能够守护", "动词可能形"), item("もの", "事物；东西", "形式名词"),
        item("は", "提示主题", "提示助词", function=True), item("この", "这个", "连体词"),
        item("瞬間", "瞬间", "名词"), item("だけ", "限定范围：只有", "副助词", function=True),
    ],
    "一緒に行こう あたしを信じて": [
        item("一緒に", "一起", "副词性短语"), item("行こう", "一起走吧", "动词意志形"),
        item("あたし", "我（女性口语）", "人称代词"), item("を", "标示动作对象", "格助词", function=True),
        item("信じて", "相信", "动词て形"),
    ],
    "声が聞こえた未来へ": [
        item("声", "声音", "名词"), item("が", "标示感知到的主体", "格助词", function=True),
        item("聞こえた", "听见了", "自动词た形"), item("未来", "未来", "名词"),
        item("へ", "表示前进方向", "格助词", function=True),
    ],
    "この煌めきは誰も消せないよ": [
        item("この", "这份", "连体词"), item("煌めき", "闪耀；光辉", "名词"),
        item("は", "提示主题", "提示助词", function=True), item("誰も", "谁都（与否定呼应）", "疑问代词＋も"),
        item("消せない", "无法抹去", "他动词可能否定形"), item("よ", "加强断定语气", "终助词", function=True),
    ],
    "守れるのなら引き金を引こう": [
        item("守れるのなら", "如果能够守护", "V可能形＋のなら（条件）"),
        item("引き金", "扳机", "名词"), item("を", "标示动作对象", "格助词", function=True),
        item("引こう", "扣动吧", "动词意志形"),
    ],
    "祝福をしよう新たな願いを ほら": [
        item("祝福をしよう", "来祝福吧", "名词＋をする意志形"), item("新たな", "崭新的", "ナ形容词连体形"),
        item("願い", "愿望", "名词"), item("を", "标示前置的动作对象", "格助词", function=True),
        item("ほら", "你看；来吧", "感叹词"),
    ],
    "楽しい事を選んでいこう": [
        item("楽しい", "快乐的", "イ形容词"), item("事", "事情", "形式名词"),
        item("を", "标示动作对象", "格助词", function=True),
        item("選んでいこう", "今后选择下去吧", "Vていく意志形"),
    ],
    "やりたい事を全部やろう": [
        item("やりたい", "想做", "动词ます形＋たい"), item("事", "事情", "形式名词"),
        item("を", "标示动作对象", "格助词", function=True), item("全部", "全部", "名词／副词"),
        item("やろう", "都去做吧", "动词意志形"),
    ],
    "悩む事は何もないよ": [
        item("悩む", "烦恼；苦恼", "动词"), item("事", "事情", "形式名词"),
        item("は", "提示主题", "提示助词", function=True), item("何も", "任何……都（与否定呼应）", "疑问代词＋も"),
        item("ない", "没有", "イ形容词"), item("よ", "加强告知语气", "终助词", function=True),
    ],
    "惑う暇はない": [
        item("惑う", "迷惘；犹豫", "动词"), item("暇", "空闲；工夫", "名词"),
        item("は", "提示主题", "提示助词", function=True), item("ない", "没有", "イ形容词"),
    ],
    "光あれと願う そう暗闇撃ち抜いて": [
        item("光あれ", "要有光", "名词＋ある命令形"), item("と", "标示引用内容", "格助词", function=True),
        item("願う", "祈愿", "动词"), item("そう", "没错；就这样", "副词"),
        item("暗闇", "黑暗", "名词"), item("撃ち抜いて", "击穿；贯穿", "复合动词て形"),
    ],
    "アップルパイ片手に": [
        item("アップルパイ", "苹果派", "外来语名词", source_word="apple pie"),
        item("片手に", "单手拿着", "固定短语"),
    ],
    "ねぇ何処までも行けそう": [
        item("ねぇ", "喂；你看", "感叹词"), item("何処までも", "无论到哪里；一直", "疑问词＋まで＋も"),
        item("行けそう", "好像能走下去", "动词可能形＋そう"),
    ],
    "ずっと夢から 醒めない": [
        item("ずっと", "一直", "副词"), item("夢", "梦", "名词"),
        item("から", "表示脱离的起点", "格助词", function=True), item("醒めない", "不会醒来", "动词ない形"),
    ],
    "このまま 気付いて あたしの翼で": [
        item("このまま", "就这样", "固定表达"), item("気付いて", "察觉到吧", "动词て形"),
        item("あたし", "我（女性口语）", "人称代词"), item("の", "表示所属", "格助词", function=True),
        item("翼", "翅膀", "名词"), item("で", "标示动作手段", "格助词", function=True),
    ],
    "壊して描いた空へ": [
        item("壊して", "打破；破坏", "动词て形"), item("描いた", "描绘出的", "动词た形（连体）"),
        item("空", "天空", "名词"), item("へ", "表示前进方向", "格助词", function=True),
    ],
}

CARD_SPECS["一緒に行こう あたしを信じて ほら"] = [
    *CARD_SPECS["一緒に行こう あたしを信じて"], item("ほら", "你看；来吧", "感叹词")
]
CARD_SPECS["さぁ あたしの手を取って ほら"] = [
    *CARD_SPECS["さぁ あたしの手を取って"], item("ほら", "你看；来吧", "感叹词")
]


def katakana_to_hiragana(value: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


def reading_for(token: str) -> str:
    values = []
    for part in TOKENIZER.tokenize(token):
        values.append(part.reading if part.reading != "*" else part.surface)
    return katakana_to_hiragana("".join(values))


def romaji_for(reading: str) -> str:
    return "".join(part["hepburn"] for part in KAKASI.convert(reading)).strip()


def furigana_for(cards: list[dict]) -> list[dict]:
    result = []
    for card_index, card in enumerate(cards):
        token, reading = card["token"], card["reading"]
        groups = list(re.finditer(r"[一-龯々]+", token))
        if not groups:
            continue
        if len(groups) == 1:
            group = groups[0]
            value = reading
            prefix, suffix = token[:group.start()], token[group.end():]
            if prefix and value.startswith(prefix):
                value = value[len(prefix):]
            if suffix and value.endswith(suffix):
                value = value[:-len(suffix)]
            result.append({"base": group.group(), "cardIndex": card_index, "surfaceOffset": group.start(), "reading": value or reading})
        else:
            result.append({"base": "".join(group.group() for group in groups), "cardIndex": card_index, "surfaceOffset": groups[0].start(), "reading": reading})
    return result


def card_from_spec(spec: dict) -> dict:
    reading = reading_for(spec["token"])
    card = {
        "token": spec["token"],
        "reading": reading,
        "romaji": romaji_for(reading),
        "grammarStructureZh": spec["grammarStructureZh"],
        "render": True,
        "showJlpt": False,
        "status": "draft",
        "fieldProvenance": {
            "token": "draft learning-value segmentation",
            "reading": "Janome 0.5.0 local morphology draft",
            "romaji": "pykakasi local conversion draft",
            "meaningOrFunction": "assistant draft; pending translation-role review",
            "grammarStructureZh": "assistant draft; pending grammar-role review"
        },
    }
    for key in ("zhMeaning", "functionZh", "sourceWord"):
        if key in spec:
            card[key] = spec[key]
    return card


def main() -> None:
    document = json.loads(FRAMES_PATH.read_text(encoding="utf-8"))
    unresolved = []
    for frame in document["frames"]:
        japanese = frame["caption"]["japanese"]
        specs = CARD_SPECS.get(japanese)
        if specs is None:
            unresolved.append({"id": frame["id"], "japanese": japanese})
            continue
        cards = [card_from_spec(spec) for spec in specs]
        cursor = 0
        for card in cards:
            found = japanese.find(card["token"], cursor)
            if found < 0:
                raise RuntimeError(f"Card token order mismatch: {frame['id']} {card['token']}")
            cursor = found + len(card["token"])
        frame["grammarCards"] = cards
        frame["caption"]["furigana"] = furigana_for(cards)
        frame["caption"]["romaji"] = " ".join(card["romaji"] for card in cards)
        frame["caption"]["translationStatus"] = "draft-qmts-source-needs-context-review"
        frame["status"] = "draft"
    if unresolved:
        raise RuntimeError(f"Missing card specs: {unresolved}")
    FRAMES_PATH.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    particle_table = {
        "schemaVersion": 1,
        "status": "draft",
        "rule": "助词卡显示语境功能，不显示孤立词典义。",
        "particles": {
            "に": ["动作状态", "变化结果", "对象", "方向"],
            "を": ["动作对象", "经过的时空"],
            "の": ["所属"], "は": ["主题", "对比"], "が": ["主体"],
            "へ": ["方向"], "から": ["原因", "起点"], "と": ["引用"],
            "で": ["手段"], "も": ["包含／全面否定呼应"], "だけ": ["限定"],
            "よ": ["告知／断定／劝说语气"], "ほどに": ["程度"]
        }
    }
    PARTICLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PARTICLE_PATH.write_text(json.dumps(particle_table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lines = ["# Heavenly Me 词卡审阅稿", "", "状态：初始草稿，所有词卡均待多角色审核。", ""]
    for frame in document["frames"]:
        lines += [f"## {frame['id']}  `{frame['startMs']}–{frame['endMs']} ms`", "", f"日文：{frame['caption']['japanese']}", "", f"暂定中文：{frame['caption']['translationZh']}", "", "待核词卡：", ""]
        for card in frame["grammarCards"]:
            meaning = card.get("functionZh", card.get("zhMeaning", ""))
            source = f"；原词：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(f"- {card['token']}｜{card['reading']}｜{card['romaji']}｜{meaning}｜{card['grammarStructureZh']}{source}")
        lines += [""]
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"frames": len(document["frames"]), "review": str(REVIEW_PATH), "particleTable": str(PARTICLE_PATH)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
