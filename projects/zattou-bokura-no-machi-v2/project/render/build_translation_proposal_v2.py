from __future__ import annotations

"""Full-coverage translation card proposal.

Every frame has a token sequence that reconstructs its Japanese caption after
whitespace and punctuation are ignored.  This is a proposal only: frames.json
is never changed here.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def x(token: str, zh: str, pos: str) -> dict:
    return {"token": token, "zhMeaning": zh, "posZh": pos, "grammarStructureZh": f"{token}：{zh}", "render": True, "showJlpt": False, "reviewRequired": True}


def p(token: str, function: str, pos: str = "助词") -> dict:
    return {"token": token, "functionZh": function, "posZh": pos, "grammarStructureZh": f"{token}：{function}", "render": True, "showJlpt": False, "reviewRequired": True}


# Shorthands make the semantic table legible.  All entries are ordered tokens;
# token concatenation is checked against the caption below.
L = {
"l006": [x("やり残した", "留下未完成的", "复合动词（た形）"), x("鼓動", "心跳", "名词"), p("が", "提示主语"), x("この", "这、这个", "连体词"), x("夜", "夜晚", "名词"), p("を", "提示动作对象"), x("覆って", "覆盖、笼罩", "动词（て形）")],
"l007": [x("僕ら", "我们", "代词"), p("を", "提示动作对象"), x("包んで", "包裹着、包住并", "动词（て形）"), x("粉々", "粉碎、碎片", "名词"), p("に", "表示变化结果/状态"), x("なる", "变成", "动词"), x("前", "之前", "名词"), p("に", "表示时间界限")],
"l008": [x("頼りなくても", "即使不可靠也", "形容词让步形"), x("いい", "可以、无妨", "形容词"), x("その", "那、那个", "连体词"), x("手", "手；援手", "名词"), p("を", "提示动作对象")],
"l009": [x("この", "这、这个", "连体词"), x("手", "手", "名词"), p("は", "提示主题并形成对比/强调"), x("自分", "自己", "名词"), x("自身", "自身、本身", "名词"), p("の", "所属修饰"), x("もの", "东西；属于……的东西", "形式名词"), p("さ", "加强陈述语气", "终助词")],
"l010": [x("変わらない", "不会改变", "动词否定形"), x("はず", "按理应当；预期", "形式名词"), p("は", "提示主题并强调否定"), x("ない", "没有；不", "形容词"), p("よ", "提示、强调给听者", "终助词")],
"l011": [x("手", "手", "名词"), p("を", "提示动作对象"), x("伸ばして", "伸出（手）", "动词（て形）")],
"l012": [x("雑踏", "拥挤的人潮、喧闹街头", "名词"), p("の", "所属修饰"), x("中", "之中", "名词"), p("で", "表示动作发生的场所"), x("声", "声音", "名词"), x("無き", "没有……的", "连体词性表达"), x("声", "声音", "名词"), p("で", "表示动作方式/状态"), x("泣いて", "哭泣着", "动词（て形）"), x("いる", "正在；持续", "补助动词")],
"l013": [x("足跡", "足迹", "名词"), p("が", "提示主语"), x("今", "此刻、现在", "名词"), x("誰か", "某人", "不定代词"), p("の", "所属修饰"), x("声", "声音", "名词"), p("を", "提示动作对象"), x("消した", "消去了、抹去了", "动词（た形）"), x("朝", "清晨", "名词")],
"l014": [x("いつ", "何时", "疑问代词"), p("に", "表示变化到达的时间"), x("なっても", "即使变成……也", "让步表达"), x("枯れる", "枯萎、枯竭", "动词"), x("こと", "事情；……这一情况", "形式名词"), p("の", "连接修饰"), x("ない", "没有；不", "形容词")],
"l015": [x("腐敗", "腐败", "名词"), x("した", "做了的；已……的", "动词（た形）"), x("街", "城市、街道", "名词"), p("の", "所属修饰"), x("泥水", "泥水", "名词"), p("が", "提示主语"), x("冷たい", "冰冷的", "形容词")],
"l016": [x("何", "什么", "疑问代词"), p("にも", "与否定呼应，表示‘什么也’"), x("変わらない", "不改变", "动词否定形"), x("世界", "世界", "名词"), p("で", "表示范围、场合")],
"l017": [x("今日", "今天", "名词"), p("だって", "即使是……也；……依然", "提示表达"), x("生きて", "活着、生活着", "动词（て形）"), x("ゆく", "持续……下去", "补助动词"), p("んだ", "说明、强调语气", "终助表达")],
"l018": [x("くだらない", "毫无意义的、无聊的", "形容词"), p("けど", "表示转折或铺垫", "接续助词"), x("仕方ない", "没办法、无可奈何", "固定表达"), p("でしょ", "表示确认、推测‘吧’", "助动词")],
"l019": [x("僕ら", "我们", "代词"), p("は", "提示主题"), x("もう", "已经", "副词"), x("歩き", "走、迈步", "动词连用形"), x("始めた", "开始了", "补助动词（た形）"), p("んだ", "说明、强调语气", "终助表达")],
"l020": [x("嘘", "谎言", "名词"), x("みたいな", "像……一样的", "比况表达"), x("馬鹿", "傻瓜", "名词"), x("みたいな", "像……一样的", "比况表达")],
"l021": [x("どうしようもない", "无可奈何、无药可救", "固定表达"), x("僕ら", "我们", "代词"), p("の", "所属修饰"), x("街", "城市、街道", "名词")],
"l022": [x("それでも", "即便如此、尽管如此", "接续副词")],
"l023": [x("この", "这、这个", "连体词"), x("眼", "眼睛", "名词"), p("で", "表示手段、工具"), x("確かに", "确实地、的确", "副词"), x("見えた", "看见了；能看见", "动词（た形）"), p("んだ", "说明、强调语气", "终助表达")],
"l024": [x("この", "这、这个", "连体词"), x("手", "手", "名词"), p("で", "表示手段、工具"), x("確かに", "确实地、的确", "副词"), x("触れた", "触碰到了", "动词（た形）"), p("んだ", "说明、强调语气", "终助表达")],
"l025": [x("ねえ", "喂；呐（唤起注意）", "感叹词"), x("ほら", "你看；瞧", "感叹词"), x("ほら", "你看；瞧", "感叹词")],
"l026": [x("ほら", "你看；瞧", "感叹词"), x("また", "又、再次", "副词"), x("吹いた", "吹起了、拂过了", "动词（た形）"), x("馬鹿", "傻瓜", "名词"), x("みたいだ", "像……一样", "比况表达")],
"l027": [x("どうしようもない", "无可奈何、无药可救", "固定表达"), x("闇", "黑暗", "名词"), p("を", "提示动作对象"), x("照らせ", "照亮吧", "动词命令形")],
"l028": [x("夢", "梦境", "名词"), x("じゃない", "不是", "否定表达")],
"l029": [x("どうせ", "反正、终究", "副词"), x("終わってる", "已经结束了、完了", "动词（口语完成状态）"), x("街", "城市、街道", "名词"), p("だって", "即使是……也", "提示表达")],
"l030": [x("諦めたって", "即使放弃也", "让步表达"), x("変わんない", "不会改变", "动词否定口语形"), p("ぜ", "加强断言语气", "终助词")],
"l031": [x("ああ", "啊啊", "感叹词"), x("まだ", "仍然、还", "副词"), x("まだ", "仍然、还", "副词"), x("まだ", "仍然、还", "副词")],
"l038": [x("永遠", "永恒", "名词"), p("の", "所属修饰"), x("中", "之中", "名词"), p("で", "表示范围、场合"), x("迷わない", "不迷失、不犹豫", "动词否定形"), x("為", "为了；目的", "名词"), p("の", "所属修饰"), x("温もり", "温暖、暖意", "名词")],
"l039": [x("軽薄", "轻率、轻浮", "形容动词词干"), x("な", "连接形容动词与名词", "助动词", True) if False else p("な", "连接形容动词与名词", "助动词"), x("君", "你", "代词"), p("に", "表示对象、方向")],
"l040": [x("届く", "传达、送到", "动词"), x("こと", "事情；……这一情况", "形式名词"), p("なく", "表示‘不……而’", "接续助词"), x("散って", "消散着", "动词（て形）"), x("ゆく", "逐渐……下去", "补助动词")],
"l041": [x("想像", "想象", "名词"), x("通り", "如同、按照", "形式名词"), x("そんな", "那样的", "连体词"), x("はず", "按理应当；预期", "形式名词"), p("は", "提示主题并强调否定"), x("ない", "没有；不", "形容词")],
"l042": [x("逃げりゃ", "如果逃跑的话（逃げれば的口语缩约）", "条件表达"), x("いい", "可以、无妨", "形容词"), p("でしょ", "表示确认、推测‘吧’", "助动词")],
"l043": [x("簡単", "简单、轻易", "形容动词词干"), p("に", "使形容动词作状语"), x("言わない", "不说", "动词否定形"), p("で", "表示否定请求‘不要……’", "接续助词")],
"l044": [x("いつも", "总是、平时", "副词"), x("通り", "如同、按照", "形式名词"), p("の", "所属修饰"), x("世界", "世界", "名词"), p("を", "提示动作对象")],
"l045": [x("今日", "今天", "名词"), p("だって", "即使是……也；……依然", "提示表达"), x("駆けて", "奔跑着", "动词（て形）"), x("ゆく", "持续……下去", "补助动词"), p("んだ", "说明、强调语气", "终助表达")],
"l046": [x("滑り", "滑、滑落", "动词连用形"), x("落ちたら", "如果落下的话", "条件表达"), x("掴んで", "抓住", "动词（て形）"), x("やろう", "我来……吧；为你……", "补助动词意志形")],
"l047": [x("灰色", "灰色", "名词"), p("の", "所属修饰"), x("空", "天空", "名词"), x("その", "那、那个", "连体词"), x("中", "之中", "名词"), p("で", "表示范围、场合"), x("煌めく", "闪耀、闪烁", "动词"), x("青さ", "蔚蓝；蓝色的程度", "名词"), p("を", "提示动作对象")],
"l066": [x("何もかも", "一切、全部", "代词性表达"), x("君", "你", "代词"), x("次第", "取决于；全看", "名词"), p("で", "表示依据、决定因素"), x("僕", "我", "代词"), x("次第", "取决于；全看", "名词"), p("さ", "加强陈述语气", "终助词")],
}

COPY = {
    "l032":"l006", "l033":"l007", "l034":"l008", "l035":"l009", "l036":"l010", "l037":"l011",
    "l048":"l020", "l049":"l021", "l050":"l022", "l051":"l023", "l052":"l024", "l053":"l025", "l054":"l026", "l055":"l027", "l056":"l028", "l057":"l029", "l058":"l030", "l059":"l031",
    "l060":"l006", "l061":"l007", "l062":"l008", "l063":"l009", "l064":"l010", "l065":"l011",
}


def norm(text: str) -> str:
    return re.sub(r"[\s\u3000\u3001\u3002\uff01\uff1f!?！？、。『』「」\"'・]", "", text)


def main() -> None:
    frames_path = PROJECT / "frames.json"
    data = json.loads(frames_path.read_text(encoding="utf-8"))
    complete = dict(L)
    complete.update({target: L[source] for target, source in COPY.items()})
    frame_ids = [frame["id"] for frame in data["frames"]]
    missing = [frame_id for frame_id in frame_ids if frame_id not in complete]
    if missing:
        raise SystemExit(f"missing cards: {missing}")
    assertions = []
    for frame in data["frames"]:
        tokens = complete[frame["id"]]
        expected = norm(frame["caption"]["japanese"])
        actual = norm("".join(item["token"] for item in tokens))
        assertions.append({"frameId": frame["id"], "expected": expected, "actual": actual, "passed": expected == actual, "tokenCount": len(tokens)})
    failed = [item for item in assertions if not item["passed"]]
    if failed:
        raise SystemExit("coverage assertion failed: " + json.dumps(failed, ensure_ascii=False))
    out = {
        "schemaVersion": 2,
        "reviewRole": "translation",
        "scope": {"frameIds": frame_ids},
        "baseFrameSha256": sha(frames_path),
        "changes": [{
            "frameId": frame["id"], "field": "grammarCards", "old": frame.get("grammarCards", []), "new": complete[frame["id"]],
            "confidence": "medium-high", "rationale": "Full-token coverage; QMTS complete-sentence Chinese anchors lexical meanings and particle functions."
        } for frame in data["frames"]],
        "coverage": {"assertion": "normalize(concat(card.token)) == normalize(caption.japanese)", "frames": assertions, "passed": True},
        "notes": ["61/61 lyric frames covered; no QRC metadata frames.", "Particles use functionZh; every other card uses zhMeaning.", "Repeated lyric lines use the same full token-card values."],
    }
    target = PROJECT / "proposals" / "translation-v2.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"target": str(target), "frames": len(frame_ids), "cards": sum(len(v) for v in complete.values()), "coverage": "passed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
