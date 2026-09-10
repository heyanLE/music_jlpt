from __future__ import annotations

"""Translation-role proposal: full card set, anchored to QMTS sentence translations.

This deliberately does not modify frames.json.  The grammarCards values are supplied
to the integration review as a semantic baseline for the grammar/lexical proposals.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def card(token: str, meaning: str, pos: str, function: bool = False, note: str = "") -> dict:
    item = {
        "token": token,
        "posZh": pos,
        "grammarStructureZh": note or (f"{token}：{meaning}"),
        "render": True,
        "showJlpt": False,
        "reviewRequired": True,
    }
    item["functionZh" if function else "zhMeaning"] = meaning
    return item


def c(*items: tuple) -> list[dict]:
    return [card(*item) for item in items]


# The unit choices follow the legacy review style: salient content words plus
# functional particles/constructions, not a mechanical character-by-character split.
LINE_CARDS = {
    "l006": c(
        ("やり残した", "留下未完成的", "复合动词（た形）"),
        ("が", "提示主语", "助词", True),
        ("を", "提示动作对象", "助词", True),
        ("覆って", "覆盖、笼罩", "动词（て形）"),
    ),
    "l007": c(
        ("僕ら", "我们", "代词"),
        ("包んで", "包裹着、包住并", "动词（て形）"),
        ("粉々に", "粉碎地、成碎片状", "副词性名词＋に"),
        ("前に", "在……之前", "时间表达"),
    ),
    "l008": c(
        ("頼りなくてもいい", "即使不可靠也没关系", "句型"),
        ("その", "那、那个", "连体词"),
        ("手", "手；援手", "名词"),
    ),
    "l009": c(
        ("は", "提示主题并形成对比/强调", "助词", True),
        ("自分自身", "自己本身", "名词"),
        ("もの", "东西；属于……的东西", "形式名词"),
        ("さ", "加强陈述语气", "终助词", True),
    ),
    "l010": c(
        ("変わらない", "不会改变的", "动词否定形"),
        ("はずはない", "不可能……；不应当……", "固定句型"),
        ("よ", "提示、强调给听者", "终助词", True),
    ),
    "l011": c(
        ("手", "手", "名词"),
        ("を", "提示动作对象", "助词", True),
        ("伸ばして", "伸出（手）", "动词（て形）"),
    ),
    "l012": c(
        ("雑踏", "拥挤的人潮、喧闹街头", "名词"),
        ("の中で", "在……之中", "助词复合表达", True),
        ("声無き声", "无声的声音", "名词短语"),
        ("泣いている", "正在哭泣、一直哭着", "动词（ている）"),
    ),
    "l013": c(
        ("足跡", "足迹", "名词"),
        ("誰か", "某人", "不定代词"),
        ("を", "提示动作对象", "助词", True),
        ("消した", "消去了、抹去了", "动词（た形）"),
    ),
    "l014": c(
        ("いつになっても", "无论何时都", "让步表达"),
        ("枯れる", "枯萎、枯竭", "动词"),
        ("ことのない", "从未……的；不会……的", "固定句型"),
    ),
    "l015": c(
        ("腐敗した", "腐败的", "动词（た形）"),
        ("街", "城市、街道", "名词"),
        ("泥水", "泥水", "名词"),
        ("冷たい", "冰冷的", "形容词"),
    ),
    "l016": c(
        ("何にも", "什么也……（与否定呼应）", "副词性表达"),
        ("変わらない", "不改变的", "动词否定形"),
        ("世界で", "在……世界中", "名词＋助词", True),
    ),
    "l017": c(
        ("今日だって", "即使是今天也；今天依然", "提示表达"),
        ("生きてゆく", "活下去、继续生活", "动词＋补助动词"),
        ("んだ", "说明、强调语气", "终助表达", True),
    ),
    "l018": c(
        ("くだらない", "毫无意义的、无聊的", "形容词"),
        ("けど", "表示转折或铺垫", "接续助词", True),
        ("仕方ない", "没办法、无可奈何", "固定表达"),
        ("でしょ", "吧；表示确认", "助动词", True),
    ),
    "l019": c(
        ("僕ら", "我们", "代词"),
        ("もう", "已经", "副词"),
        ("歩き始めた", "开始走起来了", "复合动词（た形）"),
        ("んだ", "说明、强调语气", "终助表达", True),
    ),
    "l020": c(
        ("嘘みたいな", "像谎言一样的；不可置信的", "比况表达"),
        ("馬鹿みたいな", "像傻瓜一样的", "比况表达"),
    ),
    "l021": c(
        ("どうしようもない", "无可奈何、无药可救", "固定表达"),
        ("僕ら", "我们", "代词"),
        ("の", "所属修饰", "助词", True),
        ("街", "城市、街道", "名词"),
    ),
    "l022": c(("それでも", "即便如此、尽管如此", "接续副词")),
    "l023": c(
        ("この", "这、这个", "连体词"),
        ("眼で", "用这双眼；凭借这双眼", "名词＋助词", True),
        ("確かに", "确实地、的确", "副词"),
        ("見えたんだ", "看见了；能看见啊", "动词＋说明语气"),
    ),
    "l024": c(
        ("この", "这、这个", "连体词"),
        ("手で", "用这双手；亲手", "名词＋助词", True),
        ("確かに", "确实地、的确", "副词"),
        ("触れたんだ", "触碰到了啊", "动词＋说明语气"),
    ),
    "l025": c(
        ("ねえ", "喂；呐（唤起注意）", "感叹词"),
        ("ほら", "你看；瞧", "感叹词"),
    ),
    "l026": c(
        ("また", "又、再次", "副词"),
        ("吹いた", "吹起了、拂过了", "动词（た形）"),
        ("馬鹿みたいだ", "像傻瓜一样", "比况表达"),
    ),
    "l027": c(
        ("どうしようもない", "无可奈何、无药可救", "固定表达"),
        ("闇", "黑暗", "名词"),
        ("を", "提示动作对象", "助词", True),
        ("照らせ", "照亮吧", "动词命令形"),
    ),
    "l028": c(("夢じゃない", "不是梦境", "否定表达")),
    "l029": c(
        ("どうせ", "反正、终究", "副词"),
        ("終わってる", "已经结束了、完了", "动词（口语完成状态）"),
        ("街", "城市、街道", "名词"),
        ("だって", "即使是……也", "助词/提示表达", True),
    ),
    "l030": c(
        ("諦めたって", "即使放弃也", "让步表达"),
        ("変わんない", "不会改变（変わらない的口语形）", "动词否定口语形"),
        ("ぜ", "加强语气", "终助词", True),
    ),
    "l031": c(("まだ", "仍然、还", "副词")),
    "l038": c(
        ("永遠", "永恒", "名词"),
        ("の中で", "在……之中", "助词复合表达", True),
        ("迷わない", "不迷失、不犹豫", "动词否定形"),
        ("為の", "为了……的", "目的表达"),
        ("温もり", "温暖、暖意", "名词"),
    ),
    "l039": c(
        ("軽薄な", "轻率的、轻浮的", "形容动词连体形"),
        ("君", "你", "代词"),
        ("に", "表示对象、方向", "助词", True),
    ),
    "l040": c(
        ("届くことなく", "未能传达就……；没有传达便……", "固定句型"),
        ("散ってゆく", "逐渐消散而去", "动词＋补助动词"),
    ),
    "l041": c(
        ("想像通り", "如想象一样、意料之中", "名词＋形式名词"),
        ("そんな", "那样的", "连体词"),
        ("はずはない", "不可能如此", "固定否定句型"),
    ),
    "l042": c(
        ("逃げりゃ", "如果逃跑的话（逃げれば的口语缩约）", "条件表达"),
        ("いいでしょ", "可以了吧；这样就行了吧", "句型"),
    ),
    "l043": c(
        ("簡単に", "轻易地、简单地", "形容动词连用形"),
        ("言わないで", "不要说……", "否定请求表达"),
    ),
    "l044": c(
        ("いつも通り", "一如既往、和平时一样", "固定表达"),
        ("の", "所属修饰", "助词", True),
        ("世界", "世界", "名词"),
        ("を", "提示动作对象", "助词", True),
    ),
    "l045": c(
        ("今日だって", "即使是今天也；今天依然", "提示表达"),
        ("駆けてゆく", "奔跑着前行", "动词＋补助动词"),
        ("んだ", "说明、强调语气", "终助表达", True),
    ),
    "l046": c(
        ("滑り落ちたら", "如果滑落的话", "条件表达"),
        ("掴んで", "抓住", "动词（て形）"),
        ("やろう", "我来……吧；为你……", "补助动词意志形"),
    ),
    "l047": c(
        ("灰色", "灰色", "名词"),
        ("空", "天空", "名词"),
        ("その中で", "在那之中", "助词复合表达", True),
        ("煌めく", "闪耀、闪烁", "动词"),
        ("青さ", "蔚蓝；蓝色的程度", "名词"),
    ),
    "l066": c(
        ("何もかも", "一切、全部", "代词性表达"),
        ("君次第で", "取决于你", "固定表达"),
        ("僕次第さ", "取决于我啊", "固定表达＋终助词"),
    ),
}

# Refrains use identical cards, which is important for user correction propagation.
COPY_FROM = {
    "l032": "l006", "l033": "l007", "l034": "l008", "l035": "l009", "l036": "l010", "l037": "l011",
    "l048": "l020", "l049": "l021", "l050": "l022", "l051": "l023", "l052": "l024", "l053": "l025",
    "l054": "l026", "l055": "l027", "l056": "l028", "l057": "l029", "l058": "l030", "l059": "l031",
    "l060": "l006", "l061": "l007", "l062": "l008", "l063": "l009", "l064": "l010", "l065": "l011",
}


def main() -> None:
    frames_path = PROJECT / "frames.json"
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    cards = dict(LINE_CARDS)
    for target, source in COPY_FROM.items():
        cards[target] = LINE_CARDS[source]
    missing = [frame["id"] for frame in data["frames"] if frame["id"] not in cards]
    if missing:
        raise SystemExit(f"missing full-card proposals: {missing}")
    changes = []
    for frame in data["frames"]:
        changes.append({
            "frameId": frame["id"],
            "field": "grammarCards",
            "old": frame.get("grammarCards", []),
            "new": cards[frame["id"]],
            "confidence": "medium-high",
            "rationale": "QMTS sentence translation anchored; content meanings, particle functions, and POS normalized for legacy card presentation.",
        })
    out = {
        "schemaVersion": 2,
        "reviewRole": "translation",
        "scope": {"frameIds": [frame["id"] for frame in data["frames"]]},
        "baseFrameSha256": sha(frames_path),
        "changes": changes,
        "notes": [
            "All 61 lyric frames are covered; QRC metadata lines are excluded.",
            "QMTS complete-sentence Chinese is the semantic anchor.",
            "Particle cards use functionZh, while lexical cards use zhMeaning.",
            "Each card keeps a short posZh for the rendered third row; longer explanation remains only in grammarStructureZh.",
            "Repeated refrains reuse identical card values.",
        ],
    }
    target = PROJECT / "proposals" / "translation.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"target": str(target), "frames": len(changes), "cards": sum(len(x["new"]) for x in changes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
