"""Apply the user-approved LOVE 2000 linguistic reanalysis."""
import copy
import json
from pathlib import Path


ROOT = Path(__file__).parent
PATH = ROOT / "love2000.frames.approved.json"
project = json.loads(PATH.read_text(encoding="utf-8"))
frames = {frame["id"]: frame for frame in project["frames"]}


def card(token, reading, romaji, meaning, pos, function=None):
    value = {
        "token": token, "reading": reading, "romaji": romaji,
        "zhMeaning": meaning, "posZh": pos, "render": True,
        "showJlpt": False, "reviewRequired": False,
    }
    if function is not None:
        value["functionZh"] = function
    return value


def replace(frame_id, cards, translation=None):
    frame = frames[frame_id]
    frame["grammarCards"] = cards
    frame["caption"]["furigana"] = [
        {"base": item["token"], "reading": item["reading"], "romaji": item["romaji"]}
        for item in cards
    ]
    frame["caption"]["romaji"] = " ".join(item["romaji"] for item in cards)
    if translation is not None:
        frame["caption"]["translationZh"] = translation
    frame["analysisStatus"] = "human-approved-assisted-reanalysis"
    frame["reviewRequired"] = False


# Opening refrain; identical refrains inherit it below.
replace("l001", [
    card("愛", "アイ", "ai", "爱", "名词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
    card("どこ", "ドコ", "doko", "哪里", "疑问代词"),
    card("から", "カラ", "kara", "起点、来源", "助词", "起点、来源"),
    card("やって", "ヤッテ", "yatte", "前来（やって来る的て形）", "动词（活用）"),
    card("くる", "クル", "kuru", "来", "动词"),
    card("の", "ノ", "no", "疑问、说明语气", "终助词", "疑问、说明语气"),
    card("でしょう", "デショウ", "deshou", "……呢", "助动词"),
])

replace("l002", [
    card("自分", "ジブン", "jibun", "自己", "名词"),
    card("の", "ノ", "no", "所属修饰", "助词", "所属修饰"),
    card("胸", "ムネ", "mune", "内心、胸口", "名词"),
    card("に", "ニ", "ni", "动作对象", "助词", "动作对象"),
    card("問いかけた", "トイカケタ", "toikaketa", "向……发问", "动词（活用）"),
])

replace("l011", [
    card("きっと", "キット", "kitto", "一定", "副词"),
    card("甘えてた", "アマエテタ", "amaeteta", "依赖、撒娇", "动词（活用）"),
    card("のかな", "ノカナ", "nokana", "是否……呢", "终助词／句末表达", "是否……呢"),
], "我一定一直都在依赖着、撒娇吧。")

replace("l012", [
    card("だから", "ダカラ", "dakara", "所以", "连词"),
    card("自分", "ジブン", "jibun", "自己", "名词"),
    card("愛して", "アイシテ", "aishite", "爱", "动词（活用）"),
    card("人", "ヒト", "hito", "人", "名词"),
    card("を", "ヲ", "wo", "直接宾语标记", "助词", "直接宾语标记"),
    card("愛して", "アイシテ", "aishite", "爱", "动词（活用）"),
    card("みたい", "ミタイ", "mitai", "想试着……", "动词（活用）"),
    card("の", "ノ", "no", "说明、语气", "终助词", "说明、语气"),
], "所以我想爱自己，也想试着去爱别人。")

replace("l014", [
    card("夢", "ユメ", "yume", "梦", "名词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
    card("いつでも", "イツデモ", "itsudemo", "总是", "固定短语"),
    card("膨らむ", "フクラム", "fukuramu", "膨胀", "动词"),
    card("ばかりで", "バカリデ", "bakaride", "只是一味地……、不断……", "固定语法"),
])
replace("l015", [
    card("誰か", "ダレカ", "dareka", "某人", "不定代词"),
    card("の", "ノ", "no", "所属修饰", "助词", "所属修饰"),
    card("思い", "オモイ", "omoi", "心意、感受", "名词"),
    card("を", "ヲ", "wo", "直接宾语标记", "助词", "直接宾语标记"),
    card("無視してた", "ムシシテタ", "mushishiteta", "一直忽视着", "动词（活用）"),
], "我一直忽视着某个人的感受。")
replace("l016", [
    card("きっと", "キット", "kitto", "一定", "副词"),
    card("いつか", "イツカ", "itsuka", "总有一天", "副词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
    card("わかってる", "ワカッテル", "wakatteiru", "明白、懂得", "动词（活用）"),
    card("のかナ", "ノカナ", "nokana", "是不是呢", "终助词／句末表达", "是不是呢"),
], "总有一天一定会明白的吧。")
replace("l017", [
    card("手放した", "テバナシタ", "tebanashita", "放开了的", "动词（活用）"),
    card("風船", "フウセン", "fuusen", "气球", "名词"),
    card("飛んでった", "トンデッタ", "tondetta", "飞走了", "动词（活用）"),
])
replace("l019", [
    card("あの頃", "アノコロ", "anokoro", "那个时候", "名词"),
    card("に", "ニ", "ni", "到达点、归着点", "助词", "到达点、归着点"),
    card("戻れやしない", "モドレヤシナイ", "modoreyashinai", "根本无法回去", "动词（否定强调）"),
    card("し", "シ", "shi", "补充、列举语气", "助词", "补充、列举语气"),
])
replace("l020", [
    card("だから", "ダカラ", "dakara", "所以", "连词"),
    card("今", "イマ", "ima", "现在", "名词"),
    card("を", "ヲ", "wo", "直接宾语标记", "助词", "直接宾语标记"),
    card("認めていたい", "ミトメテイタイ", "mitometeitai", "想一直接纳、认可", "动词（愿望）"),
    card("の", "ノ", "no", "说明、语气", "终助词", "说明、语气"),
], "所以我想接纳现在。")
replace("l021", [
    card("とても", "トテモ", "totemo", "非常", "副词"),
    card("大切な", "タイセツナ", "taisetsuna", "重要的", "形容动词"),
    card("事", "コト", "koto", "事情", "名词"),
    card("も", "モ", "mo", "即使、连……也……", "助词", "即使、连……也……"),
])
replace("l022", [
    card("見過ごしちゃった", "ミスゴシチャッタ", "misugoshichatta", "错过了", "动词（活用）"),
    card("としても", "トシテモ", "toshitemo", "即使……也……", "固定语法"),
])
replace("l024", [
    card("いつも", "イツモ", "itsumo", "总是", "副词"),
    card("言ってた", "イッテタ", "itteta", "说过、总是说", "动词（活用）"),
    card("ネ", "ネ", "ne", "呢", "终助词", "征求认同、加强感叹"),
], "你总是这么说呢。")
replace("l025", [
    card("まァ", "マァ", "maa", "嘛、哎呀", "感叹词"),
    card("どうにかなる", "ドウニカナル", "dounikanaru", "总会有办法、会好起来", "固定表达"),
    card("って", "ッテ", "tte", "口语引用", "助词", "口语引用"),
])
replace("l026", [
    card("だけど", "ダケド", "dakedo", "但是", "连词"),
    card("力まかせじゃ", "チカラマカセジャ", "chikaramakaseja", "光靠蛮力的话", "固定表达"),
])
replace("l027", [
    card("どうにもならない", "ドウニモナラナイ", "dounimonaranai", "无可奈何、毫无办法", "固定表达"),
    card("事", "コト", "koto", "事情", "名词"),
    card("も", "モ", "mo", "也", "助词", "也"),
    card("アル", "アル", "aru", "有", "动词"),
], "但是，也有光靠蛮力也无可奈何的事。")
replace("l030", [
    card("少しずつ", "スコシズツ", "sukoshizutsu", "一点一点地", "副词"),
    card("だけど", "ダケド", "dakedo", "虽然……但是……", "连词"),
    card("いろんな", "イロンナ", "ironna", "各种各样的", "连体词"),
    card("事", "コト", "koto", "事情", "名词"),
    card("が", "ガ", "ga", "主语标记", "助词", "主语标记"),
])
replace("l031", [
    card("変わって", "カワッテ", "kawatte", "改变着、改变了", "动词（活用）"),
    card("私", "ワタシ", "watashi", "我", "人称代词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
    card("ここに", "ココニ", "kokoni", "在这里", "地点、存在场所"),
    card("アル", "アル", "aru", "存在", "动词"),
], "尽管只是逐渐地，许多事已经改变，我也在这里。")
replace("l034", [
    card("なぞなぞ", "ナゾナゾ", "nazonazo", "谜语", "名词"),
    card("みたいな", "ミタイナ", "mitaina", "像……一样的", "比况表达"),
    card("愛す事", "アイスコト", "aisukoto", "去爱这件事", "名词化短语"),
    card("の", "ノ", "no", "所属修饰", "助词", "所属修饰"),
    card("意味", "イミ", "imi", "意义", "名词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
], "像谜语一样，爱的意义是……")
replace("l035", [
    card("運命", "ウンメイ", "unmei", "命运", "名词"),
    card("だけじゃなくて", "ダケジャナクテ", "dakejanakute", "不仅仅是……", "固定语法"),
])
replace("l036", [
    card("センチメンタルでもなくて", "センチメンタルデモナクテ", "senchimentarudemonakute", "也不是多愁善感", "固定语法"),
])
replace("l037", [
    card("強く見えない", "ツヨクミエナイ", "tsuyokumienai", "看似并不强大", "动词短语"),
    card("モノかナ", "モノカナ", "monokana", "也许是某种东西吧、难道是……吗", "句末表达"),
], "也许是某种看似并不强大的东西吧。")
replace("l040", [
    card("食べてみなくちゃ", "タベテミナクチャ", "tabeteminakucha", "不亲自尝试就……", "固定句型"),
    card("わからない", "ワカラナイ", "wakaranai", "不明白", "动词（否定）"),
    card("事", "コト", "koto", "事情", "名词"),
], "只有亲自尝过才会明白的事。")
replace("l041", [
    card("出会い", "デアイ", "deai", "相遇", "名词"),
    card("の", "ノ", "no", "所属修饰", "助词", "所属修饰"),
    card("引力", "インリョク", "inryoku", "引力", "名词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
    card("どれほどか", "ドレホドカ", "dorehodoka", "有多么……呢", "疑问短语"),
], "相遇的引力究竟有多么强大呢。")
replace("l044", [
    card("ニセモノ", "ニセモノ", "nisemono", "假货、赝品", "名词"),
    card("なんか", "ナンカ", "nanka", "举例、轻视强调（之类）", "副助词", "举例、轻视强调（之类）"),
    card("興味", "キョウミ", "kyoumi", "兴趣", "名词"),
    card("は", "ハ", "wa", "主题提示", "助词", "主题提示"),
    card("ない", "ナイ", "nai", "没有", "形容词"),
    card("ワ", "ワ", "wa", "呢、呀", "终助词", "女性口语语气"),
])
replace("l045", [
    card("ホンモノ", "ホンモノ", "honmono", "真货、真实的东西", "名词"),
    card("だけ", "ダケ", "dake", "范围限定", "助词", "范围限定"),
    card("見つけたい", "ミツケタイ", "mitsuketai", "想找到", "动词（愿望形）"),
])
replace("l046", [
    card("あなた", "アナタ", "anata", "你", "人称代词"),
    card("を", "ヲ", "wo", "直接宾语标记", "助词", "直接宾语标记"),
    card("ずっと", "ズット", "zutto", "一直", "副词"),
    card("探してた", "サガシテタ", "sagashiteta", "一直寻找着", "动词（活用）"),
])

# Repeated refrains use canonical cards and readings while retaining their own timestamps.
for target, source in (("l028", "l001"), ("l038", "l001"), ("l042", "l001"),
                       ("l029", "l002"), ("l039", "l002"), ("l043", "l002")):
    frames[target]["grammarCards"] = copy.deepcopy(frames[source]["grammarCards"])
    frames[target]["caption"]["furigana"] = copy.deepcopy(frames[source]["caption"]["furigana"])
    frames[target]["caption"]["romaji"] = frames[source]["caption"]["romaji"]
    frames[target]["analysisStatus"] = f"inherits-{source}-human-approved-assisted-reanalysis"
    frames[target]["reviewRequired"] = False

PATH.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Applied approved reanalysis to", PATH)
