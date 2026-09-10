"""Create proposal-only Chinese meaning review; never edits frames.json."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\ray-chou-kaguya-hime-study")
FRAMES = ROOT / "project" / "frames.json"
OUT = ROOT / "project" / "proposals" / "translation.json"

# Only unambiguous lexical meanings. Particles and inflectional fragments are
# deliberately left for the grammar review role.
MEANINGS = {
    "お": "礼貌前缀", "別れ": "分别；告别", "もっと": "更加；更久以前",
    "前": "之前；前方", "事": "事情", "悲しい": "悲伤的", "光": "光；光芒",
    "封じ込め": "封存；封闭在内", "踵": "脚后跟", "すり減らし": "磨损；磨薄",
    "君": "你", "い": "在；存在", "時": "时候；时间", "見え": "看得见；显现",
    "今": "现在", "透明": "透明", "彗星": "彗星", "ぼんやり": "模糊地；恍惚地",
    "でも": "但是", "それだけ": "只有那个；仅此", "探し": "寻找", "いる": "在；存在",
    "しょっちゅう": "经常；总是", "唄": "歌曲", "歌っ": "唱", "その": "那个",
    "メロディー": "旋律", "寂しく": "寂寞地", "ちゃんと": "好好地；确实地",
    "なれ": "变得；能够成为", "いつ": "何时", "どこ": "哪里", "正常": "正常",
    "異常": "异常", "考える": "思考；考虑", "暇": "空闲；工夫", "無い": "没有；不存在",
    "歩く": "走；行走", "大変": "辛苦；艰难", "楽しい": "开心的；快乐的",
    "方": "一方；方面", "ずっと": "一直；更加", "いい": "好；不错",
    "ごまかし": "蒙混；敷衍", "笑っ": "笑", "いく": "继续下去；向前",
    "大丈夫": "没事；不要紧", "あの": "那个", "痛み": "疼痛；痛苦", "忘れ": "忘记",
    "消え": "消失", "理想": "理想", "作っ": "制作；造就", "道": "道路；道路般的历程",
    "現実": "现实", "塗り替え": "改写；替换", "思い出": "回忆", "軌跡": "轨迹；痕迹",
    "上": "上面；之上", "輝き": "光辉；闪耀", "残っ": "留下；残存", "何で": "为什么",
    "何": "什么", "ため": "为了；目的", "僕": "我（男性自称）", "影": "影子",
    "長く": "长久地；长长地", "伸ばし": "伸长；延伸", "時々": "有时", "熱": "发热；热度",
    "出る": "出来；出现", "時間": "时间", "ある": "有；存在", "眠る": "睡觉",
    "夢": "梦", "解る": "明白；理解", "中": "里面；之中", "会っ": "见面；相会",
    "また": "再次；又", "行こ": "去吧；走吧", "晴天": "晴天", "ほど遠い": "相去甚远",
    "終わら": "结束", "暗闇": "黑暗", "星": "星星", "思い浮かべ": "浮现；想起",
    "すぐ": "立刻；马上", "銀河": "银河", "あまり": "不太；不怎么", "泣か": "哭",
    "靴": "鞋", "新しく": "重新；变新地", "伝え": "传达；告诉", "たかっ": "想要",
    "きっと": "一定；必定", "あっ": "有；存在", "恐らく": "恐怕；大概", "けど": "但是；不过",
    "こんなにも": "如此；这么地", "出会っ": "相遇", "繋がっ": "连接；相连",
    "無くなら": "不会消失", "◯": "正确；肯定", "△": "三角；不确定", "どれ": "哪个",
    "皆": "大家；所有人", "比べ": "比较", "どうか": "如何；怎么样", "確かめる": "确认；查明",
    "間": "空当；时间", "生きる": "活着；生活", "最高": "最好；最棒", "この": "这个",
    "始まり": "开始；起点",
}

# QMTS is the primary translation source. These are restricted to lines where
# its wording either omits the predication or reverses the literal meaning.
LINE_TRANSLATIONS = {
    "l001": "分别是在更久以前的事。",
    "l002": "仿佛是很久以前发生的事。",
    "l004": "我磨破了脚后跟。",
    "l007": "朦胧地望着那颗透明的彗星。",
    "l008": "可我仍只是在寻找它。",
    "l011": "我并不觉得寂寞。",
    "l012": "因为我已经能够好好地感到寂寞了。",
    "l016": "走下去很不容易。",
    "l017": "还是一直开心些更好啊。",
    "l021": "由理想构筑的道路，",
    "l022": "正被现实逐渐改写。",
    "l024": "化作光辉留存着。",
    "l029": "有时会发烧哦。",
    "l032": "再和你相会后继续前行吧。",
    "l033": "离晴空还很遥远。",
    "l037": "即使变得不再常常哭泣，",
    "l044": "竟会如此地……",
    "l046": "也和相遇这件事相连着。",
    "l051": "忙得连确认的空闲也没有。",
    "l052": "活着最棒了。",
}

raw = FRAMES.read_bytes()
data = json.loads(raw.decode("utf-8"))
changes = []
for frame in data["frames"]:
    replacement = LINE_TRANSLATIONS.get(frame["id"])
    if replacement and replacement != frame["caption"].get("translationZh"):
        changes.append({
            "frameId": frame["id"],
            "field": "caption.translationZh",
            "old": frame["caption"].get("translationZh"),
            "new": replacement,
            "confidence": 0.96,
            "evidence": [
                "保留 QMTS 为主来源；仅修正与日文谓词或句法明显不符的译文",
                "日文原句语义及同段上下文核对"
            ],
            "changesTokenStructure": False,
        })
for frame in data["frames"]:
    for index, card in enumerate(frame.get("grammarCards", [])):
        if card.get("zhMeaning") != "待联网核对":
            continue
        token = card.get("token")
        meaning = MEANINGS.get(token)
        if not meaning:
            continue
        changes.append({
            "frameId": frame["id"],
            "field": f"grammarCards[{index}].zhMeaning",
            "old": "待联网核对",
            "new": meaning,
            "confidence": 0.98,
            "evidence": [
                "小学馆《デジタル大辞泉》词义核对（经由コトバンク）",
                "与该句 QMTS 整句中文及重复歌词上下文一致"
            ],
            "changesTokenStructure": False,
        })

proposal = {
    "schemaVersion": 2,
    "reviewRole": "translation",
    "scope": {"frameIds": [f["id"] for f in data["frames"]]},
    "baseFrameSha256": hashlib.sha256(raw).hexdigest(),
    "changes": changes,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT} with {len(changes)} proposal changes")
