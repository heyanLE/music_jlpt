"""Build the grammar-review proposal without mutating frames.json."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\ray-chou-kaguya-hime-study\project")
FRAMES_PATH = ROOT / "frames.json"
raw = FRAMES_PATH.read_bytes()
frames_doc = json.loads(raw.decode("utf-8"))
frames = {frame["id"]: frame for frame in frames_doc["frames"]}
changes = []


def add(frame_id, card_index, field, new, evidence, confidence=0.99, structure=False):
    card = frames[frame_id]["grammarCards"][card_index]
    old = card.get(field)
    if old == new:
        return
    changes.append({
        "frameId": frame_id,
        "field": f"grammarCards.{card_index}.{field}",
        "old": old,
        "new": new,
        "confidence": confidence,
        "evidence": evidence,
        "changesTokenStructure": structure,
    })


J = "《日语教育语法核对》"
P = "《JLPT 官方样题与指南：助词、活用语和句法形式需按语境解释》"
NANTE = "《毎日のんびり日本語教師：など／なんか／なんて为口语列举、轻视或意外表达》"

# 名词化、说明语气、条件／原因等高学习价值结构。
add("l001", 4, "grammarStructureZh", "形式名词", [J, "动词过去式＋の把“分别”名词化，后接は。"])
add("l001", 4, "functionZh", "将“分别”这一动作名词化", [J, "したのは…"])
add("l002", 5, "grammarStructureZh", "比况表达", [J, "だったような中的よう表示‘仿佛／似乎’。"])
add("l003", 4, "grammarStructureZh", "接续助词", [P, "封じ込めて连接后续动作或状态。"])
add("l003", 4, "functionZh", "连接后续动作／状态", [P, "封じ込めて"])
add("l004", 3, "grammarStructureZh", "形式名词", [J, "过去式＋んだ的ん为の的口语缩约，构成说明语气。"], structure=True)
add("l004", 3, "functionZh", "与だ构成说明、强调语气", [J, "すり減らしたんだ"], structure=True)
add("l004", 4, "grammarStructureZh", "断定助动词", [J, "んだ中的だ构成说明判断。"], structure=True)
add("l004", 4, "functionZh", "与ん构成说明、强调语气", [J, "すり減らしたんだ"], structure=True)
add("l005", 1, "functionZh", "表示共同经历的对象", [J, "君といた時"])
add("l006", 3, "grammarStructureZh", "否定助动词连用形", [J, "見えなくなる中的なく为ない的连用形。"])
add("l006", 4, "grammarStructureZh", "变化表达", [J, "〜なくなる表示变得不再…。"], structure=True)
add("l006", 4, "functionZh", "与なく构成“变得不再…”", [J, "見えなくなった"], structure=True)
add("l007", 1, "grammarStructureZh", "形容动词连体形", [J, "透明な中的な连接名词。"])
add("l007", 5, "grammarStructureZh", "副词化助词", [J, "ぼんやりと中的と使拟态副词化。"])
add("l007", 5, "functionZh", "使拟态词作副词，表示模糊地", [J, "ぼんやりと"])
add("l011", 1, "grammarStructureZh", "副助词", [NANTE, "なんか用于加强否定语气。"])
add("l011", 1, "functionZh", "加强否定：一点也不…", [NANTE, "寂しくなんかなかった"])
add("l012", 4, "grammarStructureZh", "接续助词", [J, "から表示原因、理由。"])
add("l012", 4, "functionZh", "表示原因、理由：因为…", [J, "寂しくなれたから"])
add("l013", 1, "functionZh", "表示持续到的界限", [J, "いつまで"])
add("l013", 3, "functionZh", "表示范围的终点", [J, "どこまで"])
add("l013", 4, "grammarStructureZh", "副助词", [NANTE, "句末なんて带举例、轻描淡写的语气。"])
add("l013", 4, "functionZh", "列举、轻描淡写地提出“之类的”", [NANTE, "いつまでどこまでなんて"])
add("l014", 1, "grammarStructureZh", "并列助词", [J, "正常か異常か中的か连接并列选项。"])
add("l014", 1, "functionZh", "并列列出选择项", [J, "正常か異常か"])
add("l014", 3, "grammarStructureZh", "并列助词", [J, "正常か異常か中的か连接并列选项。"])
add("l014", 3, "functionZh", "并列列出选择项", [J, "正常か異常か"])
add("l014", 4, "grammarStructureZh", "副助词", [NANTE, "句末なんて带举例、轻描淡写的语气。"])
add("l014", 4, "functionZh", "列举、轻描淡写地提出“之类的”", [NANTE, "正常か異常かなんて"])
add("l015", 2, "functionZh", "与ない呼应，加强全面否定：连…也没有", [J, "暇も無い"])
add("l015", 4, "grammarStructureZh", "副助词", [J, "ほど表示程度。"])
add("l015", 4, "functionZh", "表示程度：到了…的程度", [J, "暇も無い程"])
add("l016", 1, "grammarStructureZh", "形式名词", [J, "动词辞书形＋の名词化，后接は。"])
add("l016", 1, "functionZh", "将“走路”这一动作名词化", [J, "歩くのは大変だ"])
add("l018", 1, "grammarStructureZh", "接续助词", [P, "て形连接连续动作。"])
add("l018", 1, "functionZh", "连接“掩饰”与后续动作", [P, "ごまかして笑っていく"])
add("l018", 3, "grammarStructureZh", "接续助词", [P, "て形连接补助动词いく。"])
add("l018", 3, "functionZh", "连接动作与いく，表示向后延续", [P, "笑っていく"])
add("l018", 4, "grammarStructureZh", "补助动词", [J, "〜ていく表示动作或变化向后持续。"])
add("l018", 4, "functionZh", "表示动作将继续下去", [J, "笑っていく"])
add("l020", 2, "grammarStructureZh", "接续助词", [J, "たって是ても的口语让步形式。"], 0.98, True)
add("l020", 2, "functionZh", "与た构成让步：即使忘了也…", [J, "忘れたって"], 0.98, True)
add("l020", 4, "grammarStructureZh", "强调否定表达", [J, "〜やしない为〜はしない的口语强调。"], 0.98, True)
add("l020", 4, "functionZh", "与ない构成强烈否定：绝不会…", [J, "消えやしない"], 0.98, True)
add("l020", 5, "grammarStructureZh", "否定助动词", [J, "消えやしない中的ない完成强调否定。"], 0.98, True)
add("l022", 3, "grammarStructureZh", "接续助词", [P, "て形连接补助动词いく。"])
add("l022", 3, "functionZh", "连接动作与いく，表示向后变化", [P, "塗り替えていく"])
add("l022", 4, "grammarStructureZh", "补助动词", [J, "〜ていく表示变化逐步向后发展。"])
add("l022", 4, "functionZh", "表示变化将持续推进", [J, "塗り替えていく"])
add("l024", 1, "functionZh", "表示变化后的结果状态", [J, "輝きになる"])
add("l024", 2, "grammarStructureZh", "变化表达", [J, "〜になる表示变成…。"], structure=True)
add("l024", 2, "functionZh", "与に构成“变成…”", [J, "輝きになって"], structure=True)
add("l024", 3, "grammarStructureZh", "接续助词", [P, "なって连接后续状态。"])
add("l024", 5, "grammarStructureZh", "接续助词", [P, "残っている中的て连接持续体。"])
add("l024", 6, "grammarStructureZh", "补助动词", [J, "〜ている表示结果持续。"])
add("l024", 6, "functionZh", "表示结果仍持续存在", [J, "残っている"])
add("l026", 5, "grammarStructureZh", "形式名词", [J, "んだろう中的ん为の的口语缩约，带说明语气。"], structure=True)
add("l026", 5, "functionZh", "与だろう构成说明性的自问", [J, "何のためだったんだろうな"], structure=True)
add("l026", 6, "grammarStructureZh", "推量助动词", [J, "だろう表示推量、自问。"], structure=True)
add("l026", 6, "functionZh", "与う构成推量、自问", [J, "んだろうな"], structure=True)
add("l026", 7, "grammarStructureZh", "推量助动词", [J, "だろう表示推量、自问。"], structure=True)
add("l026", 8, "grammarStructureZh", "终助词", [J, "句末な表达自言自语、感叹。"])
add("l026", 8, "functionZh", "加强自言自语、自问语气", [J, "んだろうな"])
add("l028", 4, "grammarStructureZh", "接续助词", [P, "て形连接持续体いる。"])
add("l028", 5, "grammarStructureZh", "补助动词", [J, "〜ている表示动作持续。"])
add("l028", 5, "functionZh", "表示动作正在持续", [J, "伸ばしている"])
add("l031", 2, "grammarStructureZh", "引用助词", [J, "普通形＋と解る中的と引用判断内容。"])
add("l031", 2, "functionZh", "引用“是梦”这一判断内容", [J, "夢だと解る"])
add("l032", 2, "grammarStructureZh", "接续助词", [P, "会ってから中的て连接时间顺序。"])
add("l032", 3, "grammarStructureZh", "接续助词", [J, "〜てから表示先后顺序。"], structure=True)
add("l032", 3, "functionZh", "表示先发生“相会”，再做后项", [J, "会ってからまた行こう"], structure=True)
add("l033", 1, "functionZh", "与は构成とは，提示并对比“晴天”这一概念", [J, "晴天とはほど遠い"])
add("l034", 4, "functionZh", "与に构成にも，表示“即使在…中也”", [J, "暗闇にも"], structure=True)
add("l035", 3, "grammarStructureZh", "条件表达", [J, "过去式＋なら表示假定条件。"])
add("l035", 3, "functionZh", "表示假定：如果浮现出星星…", [J, "思い浮かべたなら"])
add("l037", 2, "grammarStructureZh", "否定助动词连用形", [J, "泣かなくなる中的なく为ない的连用形。"])
add("l037", 3, "grammarStructureZh", "变化表达", [J, "〜なくなる表示变得不再…。"], structure=True)
add("l037", 3, "functionZh", "与なく构成“变得不再…”", [J, "泣かなくなっても"], structure=True)
add("l037", 4, "grammarStructureZh", "接续助词", [P, "て形连接后续让步助词も。"])
add("l037", 5, "functionZh", "表示让步：即使…也…", [J, "泣かなくなっても"])
add("l038", 2, "grammarStructureZh", "形容词连用形", [J, "新しくする中的新しく为形容词连用形。"])
add("l038", 4, "grammarStructureZh", "接续助词", [P, "て形连接让步助词も。"])
add("l038", 5, "functionZh", "表示让步：即使…也…", [J, "新しくしても"])
add("l041", 1, "grammarStructureZh", "愿望表达过去式", [J, "〜たかった为たい的过去式，表示曾想…。"])
add("l041", 2, "grammarStructureZh", "助动词", [J, "たかった中的た构成过去。"])
add("l041", 3, "grammarStructureZh", "形式名词", [J, "动词短语＋こと将动作内容名词化。"])
add("l041", 3, "functionZh", "将“想传达”这一内容名词化", [J, "伝えたかった事"])
add("l042", 3, "grammarStructureZh", "形式名词", [J, "んだろう中的ん为の的口语缩约，带说明语气。"], structure=True)
add("l042", 3, "functionZh", "与だろう构成说明性的推量", [J, "きっとあったんだろうな"], structure=True)
add("l042", 4, "grammarStructureZh", "推量助动词", [J, "だろう表示推量。"], structure=True)
add("l042", 4, "functionZh", "与う构成推量", [J, "んだろうな"], structure=True)
add("l042", 5, "grammarStructureZh", "推量助动词", [J, "だろう表示推量。"], structure=True)
add("l042", 6, "grammarStructureZh", "终助词", [J, "句末な表达自言自语、感叹。"])
add("l042", 6, "functionZh", "加强自言自语、感叹语气", [J, "んだろうな"])
add("l043", 4, "grammarStructureZh", "形式名词", [J, "なんだろう中的ん为の的口语缩约，带说明语气。"], structure=True)
add("l043", 5, "grammarStructureZh", "推量助动词", [J, "だろう表示推量。"], structure=True)
add("l043", 6, "grammarStructureZh", "推量助动词", [J, "だろう表示推量。"], structure=True)
add("l043", 7, "grammarStructureZh", "接续助词", [J, "けど表示转折、铺垫。"])
add("l043", 7, "functionZh", "表示转折、铺垫后续", [J, "ありきたりなんだろうけど"])
add("l046", 3, "functionZh", "表示“与…相连”的对象", [J, "出会った事と繋がっている"])
add("l046", 5, "grammarStructureZh", "接续助词", [P, "て形连接持续体いる。"])
add("l046", 6, "grammarStructureZh", "补助动词", [J, "〜ている表示状态持续。"])
add("l046", 6, "functionZh", "表示相连的状态持续", [J, "繋がっている"])
add("l047", 2, "grammarStructureZh", "形容动词连体形", [J, "透明な中的な连接名词。"])
add("l048", 1, "grammarStructureZh", "断定助动词", [J, "透明だから中的だ表示断定。"], structure=True)
add("l048", 2, "grammarStructureZh", "接续助词", [J, "だから表示原因、理由。"], structure=True)
add("l048", 2, "functionZh", "与だ构成原因：因为…", [J, "透明だから"], structure=True)
add("l049", 4, "grammarStructureZh", "选择助词", [J, "どれか中的か表示不定选择。"])
add("l049", 4, "functionZh", "表示不确定的选择：哪一个／某一个", [J, "どれか"])
add("l049", 5, "grammarStructureZh", "副助词", [NANTE, "句末なんて带举例、轻描淡写语气。"])
add("l049", 5, "functionZh", "列举、轻描淡写地提出“之类的”", [NANTE, "どれかなんて"])
add("l050", 1, "functionZh", "表示比较的对象：与大家相比", [J, "皆と比べて"])
add("l050", 3, "grammarStructureZh", "接续助词", [P, "比べて连接后续判断。"])
add("l050", 5, "grammarStructureZh", "副助词", [NANTE, "句末なんて带举例、轻描淡写语气。"])
add("l050", 5, "functionZh", "列举、轻描淡写地提出“如何”之类的判断", [NANTE, "どうかなんて"])
add("l051", 2, "functionZh", "与ない呼应，加强全面否定：连…也没有", [J, "間も無い"])
add("l051", 4, "grammarStructureZh", "副助词", [J, "ほど表示程度。"])
add("l051", 4, "functionZh", "表示程度：到了…的程度", [J, "間も無い程"])
add("l052", 1, "grammarStructureZh", "形式名词", [J, "动词辞书形＋の名词化，后接は。"])
add("l052", 1, "functionZh", "将“活着”这一动作名词化", [J, "生きるのは最高だ"])
add("l053", 2, "grammarStructureZh", "否定助动词连用形", [J, "泣かなくなる中的なく为ない的连用形。"])
add("l053", 3, "grammarStructureZh", "变化表达", [J, "〜なくなる表示变得不再…。"], structure=True)
add("l053", 3, "functionZh", "与なく构成“变得不再…”", [J, "泣かなくなっても"], structure=True)
add("l053", 4, "grammarStructureZh", "接续助词", [P, "て形连接后续让步助词も。"])
add("l053", 5, "functionZh", "表示让步：即使…也…", [J, "泣かなくなっても"])
add("l054", 1, "grammarStructureZh", "接续助词", [P, "て形连接连续动作。"])
add("l054", 1, "functionZh", "连接“掩饰”与后续动作", [P, "ごまかして笑っていく"])
add("l054", 3, "grammarStructureZh", "接续助词", [P, "て形连接补助动词いく。"])
add("l054", 3, "functionZh", "连接动作与いく，表示向后延续", [P, "笑っていく"])
add("l054", 4, "grammarStructureZh", "补助动词", [J, "〜ていく表示动作或变化向后持续。"])
add("l054", 4, "functionZh", "表示动作将继续下去", [J, "笑っていく"])
add("l056", 2, "grammarStructureZh", "接续助词", [J, "たって是ても的口语让步形式。"], 0.98, True)
add("l056", 2, "functionZh", "与た构成让步：即使忘了也…", [J, "忘れたって"], 0.98, True)
add("l056", 4, "grammarStructureZh", "强调否定表达", [J, "〜やしない为〜はしない的口语强调。"], 0.98, True)
add("l056", 4, "functionZh", "与ない构成强烈否定：绝不会…", [J, "消えやしない"], 0.98, True)
add("l056", 5, "grammarStructureZh", "否定助动词", [J, "消えやしない中的ない完成强调否定。"], 0.98, True)
add("l057", 5, "functionZh", "表示时间／场合：在这道光的开端", [J, "始まりに"])
add("l057", 6, "functionZh", "与に构成には，提示时间、场合为主题", [J, "始まりには"])

proposal = {
    "schemaVersion": 2,
    "reviewRole": "grammar",
    "scope": {"frameIds": [frame["id"] for frame in frames_doc["frames"]], "coverage": "all-japanese-lyric-and-user-supplied-spoken-frames"},
    "baseFrameSha256": hashlib.sha256(raw).hexdigest(),
    "changes": changes,
    "reviewNotes": [
        "已覆盖全部 60 帧；仅写入高置信、适合学习展示的助词功能、活用与句型提案。普通名词及无需改变学习解释的基础词性不提案。",
        "标记 changesTokenStructure=true 的项目是需要词法角色在整合时考虑合并的固定语法（如んだ、たって、やしない、〜なくなる）；本提案本身不会改动 frames.json。",
        "重复段落保持同一语法解释，便于整合时同步采用。",
        "MV 前段两条用户提供台词保留为受保护内容，未提出改动。",
    ],
}
(ROOT / "proposals" / "grammar.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(changes)} changes; base={proposal['baseFrameSha256']}")
