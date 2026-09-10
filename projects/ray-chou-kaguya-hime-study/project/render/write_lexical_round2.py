import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\ray-chou-kaguya-hime-study")
FRAMES_PATH = ROOT / "project" / "frames.json"
OUT = ROOT / "project" / "proposals" / "lexical-round2.json"

raw = FRAMES_PATH.read_bytes()
frames_doc = json.loads(raw)
frames = {f["id"]: f for f in frames_doc["frames"]}

def card(token, reading, romaji, grammar, pos, *, meaning=None, function=None, source_word=None):
    value = {
        "token": token,
        "reading": reading,
        "romaji": romaji,
        "grammarStructureZh": grammar,
        "posZh": pos,
        "status": "assisted-proposal",
        "fieldProvenance": {
            "token": "lexical round2 proposal",
            "reading": "lexical round2 proposal",
            "romaji": "lexical round2 proposal",
            "grammarStructureZh": "lexical round2 proposal"
        }
    }
    if meaning is not None:
        value["zhMeaning"] = meaning
    if function is not None:
        value["functionZh"] = function
    if source_word is not None:
        value["sourceWord"] = source_word
    return value

def grammar_change(frame_id, new_cards, note):
    return {
        "frameId": frame_id,
        "field": "grammarCards",
        "old": frames[frame_id]["grammarCards"],
        "new": new_cards,
        "confidence": 0.99,
        "evidence": [
            "国語辞書的活用切分与歌唱读音复核",
            note
        ],
        "changesTokenStructure": True,
        "doesNotModify": ["caption.translationZh"]
    }

def romaji_change(frame_id, new, note):
    return {
        "frameId": frame_id,
        "field": "caption.romaji",
        "old": frames[frame_id]["caption"]["romaji"],
        "new": new,
        "confidence": 0.99,
        "evidence": ["词形合并后按读音重写罗马音", note],
        "changesTokenStructure": False,
        "doesNotModify": ["caption.translationZh"]
    }

changes = []

# 这些位置上一轮把活用、助词或形式名词不恰当地粘成了一个“词”。本轮仅提出
# 可由原句字面和标准活用唯一确定的拆分，整句译文不在任何 change 中出现。
changes.append(grammar_change("l005", [
    card("君", "きみ", "kimi", "名词", "名词", meaning="你"),
    card("と", "と", "to", "格助词", "格助词", function="表示共同的对象"),
    card("いた", "いた", "ita", "动词过去式", "动词", meaning="在；存在（过去式）"),
    card("時", "とき", "toki", "名词", "名词", meaning="时候"),
    card("は", "は", "wa", "提示助词", "提示助词", function="提示主题"),
    card("見えた", "みえた", "mieta", "动词过去式", "动词", meaning="看得见；显现（过去式）"),
], "いる→いた、見える→見えた均为可唯一确定的过去式；避免将两个词干与た拆成孤立词卡。"))
changes.append(romaji_change("l005", "kimi to ita toki wa mieta", "助词は按实际读音写作 wa。"))

changes.append(grammar_change("l012", [
    card("ちゃんと", "ちゃんと", "chanto", "副词", "副词", meaning="好好地；确实地"),
    card("寂しく", "さびしく", "sabishiku", "形容词连用形", "形容词", meaning="寂寞地"),
    card("なれた", "なれた", "nareta", "动词过去式", "动词", meaning="变得；能够成为（过去式）"),
    card("から", "から", "kara", "接续助词", "接续助词", function="表示原因、理由"),
], "なれる的过去式なれた不可拆成なれ＋た作为两张独立词汇卡。"))
changes.append(romaji_change("l012", "chanto sabishiku nareta kara", "なれた合写。"))

changes.append(grammar_change("l021", [
    card("理想", "りそう", "risou", "名词", "名词", meaning="理想"),
    card("で", "で", "de", "格助词", "格助词", function="表示方式、手段"),
    card("作った", "つくった", "tsukutta", "动词过去式", "动词", meaning="制作；构筑（过去式）"),
    card("道", "みち", "michi", "名词", "名词", meaning="道路；人生道路"),
    card("を", "を", "wo", "格助词", "格助词", function="标记动作对象"),
], "理想で、道を均为名词＋格助词，需保留助词的独立学习卡。"))

changes.append(grammar_change("l034", [
    card("終わらない", "おわらない", "owaranai", "动词否定形", "动词", meaning="不会结束；无尽的"),
    card("暗闇", "くらやみ", "kurayami", "名词", "名词", meaning="黑暗"),
    card("に", "に", "ni", "格助词", "格助词", function="提示对象、处所"),
    card("も", "も", "mo", "副助词", "副助词", function="表示追加或让步"),
], "終わる的未然形＋ない构成一个否定活用，不能将终わら作为孤立动词词卡。"))
changes.append(romaji_change("l034", "owaranai kurayami ni mo", "否定形合写。"))

changes.append(grammar_change("l035", [
    card("星", "ほし", "hoshi", "名词", "名词", meaning="星星"),
    card("を", "を", "wo", "格助词", "格助词", function="标记动作对象"),
    card("思い浮かべた", "おもいうかべた", "omoiukabeta", "动词过去式", "动词", meaning="在脑海中浮现；想起（过去式）"),
    card("なら", "なら", "nara", "条件表达", "助动词", function="表示假定条件：如果…"),
], "思い浮かべる是固定复合动词；思い浮かべた必须作为完整过去式呈现。"))
changes.append(romaji_change("l035", "hoshi wo omoiukabeta nara", "复合动词过去式合写。"))

changes.append(grammar_change("l041", [
    card("伝えたかった", "つたえたかった", "tsutaetakatta", "愿望表达过去式", "动词", meaning="曾想传达"),
    card("事", "こと", "koto", "形式名词", "名词", meaning="事情；内容"),
    card("が", "が", "ga", "格助词", "格助词", function="标记主语"),
], "事が为形式名词＋主格助词，合并会掩盖が的功能。"))

changes.append(grammar_change("l045", [
    card("お別れ", "おわかれ", "owakare", "名词", "名词", meaning="分别"),
    card("した", "した", "shita", "动词过去式", "动词", meaning="做；进行（过去式）"),
    card("事", "こと", "koto", "形式名词", "名词", meaning="事情；这一事实"),
    card("は", "は", "wa", "提示助词", "提示助词", function="提示主题"),
], "事は为形式名词＋提示助词，应保留独立助词卡。"))
changes.append(romaji_change("l045", "owakare shita koto wa", "助词は按实际读音写作 wa。"))

changes.append(grammar_change("l046", [
    card("出会った", "であった", "deatta", "动词过去式", "动词", meaning="相遇（过去式）"),
    card("事", "こと", "koto", "形式名词", "名词", meaning="事情；这一事实"),
    card("と", "と", "to", "格助词", "格助词", function="表示共同或连接对象"),
    card("繋がっている", "つながっている", "tsunagatte iru", "动词持续状态", "动词", meaning="正相连着；持续相连"),
], "出会った事と由过去式、形式名词、格助词组成，不宜压成单一词卡。"))

changes.append(grammar_change("l048", [
    card("透明", "とうめい", "toumei", "名词／形容动词词干", "名词", meaning="透明"),
    card("だから", "だから", "dakara", "接续助词", "接续助词", function="表示原因：因为…"),
    card("無くならない", "なくならない", "nakunaranai", "动词否定形", "动词", meaning="不会消失"),
], "透明だから为名词性谓语＋だから，拆分后可正确展示原因表达。"))

changes.append(grammar_change("l057", [
    card("大丈夫だ", "だいじょうぶだ", "daijoubu da", "名词性谓语", "名词", meaning="没关系；没问题"),
    card("この", "この", "kono", "连体词", "连体词", meaning="这个"),
    card("光", "ひかり", "hikari", "名词", "名词", meaning="光芒"),
    card("の", "の", "no", "格助词", "格助词", function="表示所属或修饰"),
    card("始まり", "はじまり", "hajimari", "名词", "名词", meaning="开始；起点"),
    card("に", "に", "ni", "格助词", "格助词", function="提示时间或场合"),
    card("は", "は", "wa", "提示助词", "提示助词", function="提示主题"),
], "光の始まりには是名词短语＋助词，需拆分为可学习的词和助词卡。"))
changes.append(romaji_change("l057", "daijoubu da kono hikari no hajimari ni wa", "助词は按实际读音写作 wa。"))

document = {
    "schemaVersion": 2,
    "reviewRole": "lexical-round2",
    "baseFrameSha256": hashlib.sha256(raw).hexdigest(),
    "scope": {
        "allowedFields": ["grammarCards", "caption.furigana", "caption.romaji"],
        "forbiddenFields": ["caption.translationZh"],
        "policy": "仅高置信词汇切分、读音、罗马音与外来语复核；不修改整句中文。"
    },
    "sources": [
        {
            "title": "goo 国語辞書・小学館類語例解辞典",
            "url": "https://dictionary.goo.ne.jp/"
        },
        {
            "title": "日本語教育用的标准活用与格助词切分",
            "note": "与当前冻结的 QM/罗马音逐字对照。"
        }
    ],
    "changes": changes,
    "summary": {
        "highConfidenceChanges": len(changes),
        "grammarCardRevisions": sum(1 for c in changes if c["field"] == "grammarCards"),
        "captionRomajiRevisions": sum(1 for c in changes if c["field"] == "caption.romaji"),
        "captionFuriganaRevisions": 0,
        "loanwordRevisions": 0,
        "notes": [
            "メロディー→melody 的外来语注释已存在，未重复提案。",
            "没有发现可由当前词面唯一确定、需要新增或修正的汉字振假名。"
        ]
    }
}

OUT.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUT)
