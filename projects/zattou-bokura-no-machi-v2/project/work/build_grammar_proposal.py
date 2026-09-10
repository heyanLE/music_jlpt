import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\zattou-bokura-no-machi-v2")
FRAMES = ROOT / "project" / "frames.json"
OUT = ROOT / "project" / "proposals" / "grammar.json"

def card(token, reading, romaji, meaning, pos, structure, particle=False):
    result = {
        "token": token, "reading": reading, "romaji": romaji,
        "posZh": pos, "grammarStructureZh": structure,
        "render": True, "showJlpt": False, "reviewRequired": True,
    }
    result["functionZh" if particle else "zhMeaning"] = meaning
    return result

# Short, renderable learning cards.  The fifth field is deliberately only the
# part of speech; grammarStructureZh remains available to the review/renderer.
C = {
"l006": [card("やり残した","やりのこした","yarinokoshita","留下未完成的","复合动词（た形）","やり残す：做后仍有未完成部分"),card("が","が","ga","提示主语","助词","名词＋が＋谓语",True),card("を","を","o","提示动作对象","助词","名词＋を＋他动词",True),card("覆って","おおって","ootte","覆盖、笼罩","动词（て形）","覆う的て形，连接后项")],
"l007": [card("僕ら","ぼくら","bokura","我们","代词","第一人称复数"),card("を","を","o","提示动作对象","助词","名词＋を＋他动词",True),card("包んで","つつんで","tsutsunde","包裹着、包围着","动词（て形）","包む的て形，连接动作"),card("粉々になる前に","こなごなになるまえに","konagona ni naru mae ni","在粉碎之前","时间表达","动词基本形＋前に")],
"l008": [card("頼りなくてもいい","たよりなくてもいい","tayorinakute mo ii","不依赖也可以","形容词句型","形容词くて＋もいい：即使…也可以"),card("その手","そのて","sono te","那双手","连体词＋名词","その修饰手"),card("を","を","o","提示动作对象","助词","名词＋を＋他动词",True)],
"l009": [card("この手","このて","kono te","这双手","连体词＋名词","この修饰手"),card("自分自身","じぶんじしん","jibun jishin","自己本身","名词","自身加强自分"),card("の","の","no","表示所属","助词","名词＋の＋名词",True),card("ものさ","ものさ","mono sa","是…的啊","名词＋终助词","もの＋さ，带强调语气")],
"l010": [card("変わらない","かわらない","kawaranai","不会改变","动词（否定形）","変わる的ない形"),card("はずはない","はずはない","hazu wa nai","不可能、不会","句型","动词普通形＋はずはない：强烈否定"),card("よ","よ","yo","加强断言","终助词","句末提醒、强调",True)],
"l011": [card("手を伸ばして","てをのばして","te o nobashite","伸出手","惯用搭配","手を伸ばす的て形"),card("を","を","o","提示动作对象","助词","名词＋を＋他动词",True)],
"l012": [card("雑踏の中で","ざっとうのなかで","zattou no naka de","在拥挤人潮中","地点表达","名词＋の中で：在…之中"),card("声無き声","こえなきこえ","koe naki koe","无声之声","连体表达","名词＋無き：没有…的"),card("で","で","de","表示方式、状态","助词","以某种状态进行动作",True),card("泣いている","ないている","naite iru","正在哭泣","持续体","动词て形＋いる：动作进行中")],
"l013": [card("足跡","あしあと","ashiato","足迹","名词","留下的脚印"),card("が","が","ga","提示主语","助词","名词＋が＋谓语",True),card("誰か","だれか","dareka","某人","不定代词","疑问词＋か：不特定对象"),card("消した","けした","keshita","抹去、消除了","动词（た形）","消す的た形，修饰朝")],
"l014": [card("いつになっても","いつになっても","itsu ni natte mo","无论到何时都","让步表达","疑问词＋になっても：无论…都"),card("枯れることのない","かれることのない","kareru koto no nai","不会枯萎的","否定连体表达","动词基本形＋ことのない：不会…的")],
"l015": [card("腐敗した","ふはいした","fuhai shita","腐败的","名词＋する（た形）","腐敗する的た形，修饰街"),card("街の泥水","まちのどろみず","machi no doromizu","城市的泥水","名词短语","名词＋の＋名词"),card("冷たい","つめたい","tsumetai","冰冷","形容词","い形容词作谓语")],
"l016": [card("何にも","なににも","nani ni mo","无论什么都","否定呼应","何に＋も与否定谓语呼应"),card("変わらない","かわらない","kawaranai","不改变的","动词（否定形）","変わる的ない形"),card("世界で","せかいで","sekai de","在世界中","地点助词","名词＋で：动作发生的场所",True)],
"l017": [card("今日だって","きょうだって","kyou datte","即使是今天也","提示／让步","名词＋だって：也、即使"),card("生きてゆく","いきてゆく","ikite yuku","活下去","补助动词","动词て形＋ゆく：向未来持续")],
"l018": [card("くだらない","くだらない","kudaranai","无聊、没意义","形容词","い形容词"),card("けど","けど","kedo","但是、不过","接续助词","普通形＋けど：转折",True),card("仕方ない","しかたない","shikata nai","无可奈何","固定表达","仕方がない的口语省略"),card("でしょ","でしょ","desho","对吧","助动词／终助词","です＋しょう的口语，用于确认")],
"l019": [card("僕らは","ぼくらは","bokura wa","至于我们","提示主题","名词＋は：提出话题",True),card("もう","もう","mou","已经","副词","表示状态变化已经完成"),card("歩き始めた","あるきはじめた","arukihajimeta","开始迈步","复合动词（た形）","动词词干＋始める：开始做")],
"l020": [card("嘘みたいな","うそみたいな","uso mitai na","像谎言一样的","比况表达","名词＋みたいな：像…一样的"),card("馬鹿みたいな","ばかみたいな","baka mitai na","像傻瓜一样的","比况表达","名词＋みたいな：像…一样的")],
"l021": [card("どうしようもない","どうしようもない","doushiyou mo nai","无可救药、毫无办法","固定表达","どうすることもできない之意"),card("僕らの街","ぼくらのまち","bokura no machi","我们的城市","名词短语","名词＋の＋名词")],
"l022": [card("それでも","それでも","sore demo","即便如此","接续词","それ＋でも：即使那样也")],
"l023": [card("この眼で","このめで","kono me de","用这双眼睛","方式表达","名词＋で：以…作为手段",True),card("確かに","たしかに","tashika ni","确实、的确","副词","强调判断真实"),card("見えたんだ","みえたんだ","mietan da","看见了啊","说明语气","見える的た形＋のだ口语")],
"l024": [card("この手で","このてで","kono te de","用这双手","方式表达","名词＋で：以…作为手段",True),card("確かに","たしかに","tashika ni","确实、的确","副词","强调判断真实"),card("触れたんだ","ふれたんだ","furetan da","触碰到了啊","说明语气","触れる的た形＋のだ口语")],
"l025": [card("ねえ","ねえ","nee","喂、你看","感叹词","用于唤起对方注意"),card("ほら","ほら","hora","你看、瞧","感叹词","催促对方注意")],
"l026": [card("ほら","ほら","hora","你看、瞧","感叹词","催促对方注意"),card("また","また","mata","再次、又","副词","表示重复发生"),card("吹いた","ふいた","fuita","吹起了","动词（た形）","吹く的た形"),card("馬鹿みたいだ","ばかみたいだ","baka mitai da","像傻瓜一样","比况表达","名词＋みたいだ：像…一样")],
"l027": [card("どうしようもない","どうしようもない","doushiyou mo nai","无可救药、毫无办法","固定表达","どうすることもできない之意"),card("闇を","やみを","yami o","黑暗（作对象）","名词＋助词","を标记照らせ的对象",False),card("照らせ","てらせ","terase","照亮吧","动词（命令形）","照らす的命令形")],
"l028": [card("夢じゃない","ゆめじゃない","yume ja nai","不是梦","否定判断","名词＋じゃない：不是…")],
"l029": [card("どうせ","douse","dou se","反正、横竖","副词","表示不抱期待的判断"),card("終わってる","おわってる","owatteru","已经完了","结果状态","終わっている的口语缩约"),card("街だって","まちだって","machi datte","即使是城市也","提示／让步","名词＋だって：也、即使")],
"l030": [card("諦めたって","あきらめたって","akirametatte","即使放弃","让步表达","动词た形＋って（＝ても）：即使…也"),card("変わんない","かわんない","kawannai","不会改变","动词（口语否定）","変わらない的口语缩约"),card("ぜ","ぜ","ze","加强断言","终助词","较强硬的句末语气",True)],
"l031": [card("ああ","ああ","aa","啊啊","感叹词","表达感叹或呼应"),card("まだ","まだ","mada","仍然、还","副词","表示状态尚未结束")],
"l038": [card("永遠の中で","えいえんのなかで","eien no naka de","在永恒之中","地点表达","名词＋の中で：在…之中"),card("迷わない為の","まよわないための","mayowanai tame no","为了不迷失的","目的表达","否定形＋ための：为了不…的"),card("温もり","ぬくもり","nukumori","温暖","名词","温暖的感觉")],
"l039": [card("軽薄な","けいはくな","keihaku na","轻浮的","形容动词","な形容词连体形"),card("君に","きみに","kimi ni","对你、向你","对象表达","名词＋に：动作指向对象",True)],
"l040": [card("届くことなく","とどくことなく","todoku koto naku","未能传达到","否定连接","动词基本形＋ことなく：没有…就"),card("散ってゆく","ちってゆく","chitte yuku","渐渐消散","补助动词","动词て形＋ゆく：向未来变化")],
"l041": [card("想像通り","そうぞうどおり","souzou doori","如想象一般","表达","名词＋通り：按照…"),card("そんなはずはない","sonna hazu wa nai","sonna hazu wa nai","不可能那样","固定句型","そんな＋はずはない：不可能如此")],
"l042": [card("逃げりゃ","にげりゃ","nigerya","只要逃的话","条件形（口语）","逃げれば的口语缩约"),card("いいでしょ","いいでしょ","ii desho","就可以了吧","许可／确认","いい＋でしょ：可以吧")],
"l043": [card("簡単に","かんたんに","kantan ni","轻易地","形容动词副词形","な形容词＋に"),card("言わないで","いわないで","iwanai de","不要说","否定请求","动词ない形＋で：请不要…")],
"l044": [card("いつも通りの","いつもどおりの","itsumo doori no","一如往常的","表达","いつも通り＋の：一如既往的"),card("世界を","せかいを","sekai o","世界（作对象）","名词＋助词","を标记駆けてゆく的对象",False)],
"l045": [card("今日だって","きょうだって","kyou datte","即使是今天也","提示／让步","名词＋だって：也、即使"),card("駆けてゆく","かけてゆく","kakete yuku","奔跑向前","补助动词","动词て形＋ゆく：向未来持续"),card("んだ","んだ","n da","正是如此、啊","说明语气","のだ的口语形式")],
"l046": [card("滑り落ちたら","すべりおちたら","suberi ochitara","如果滑落的话","假定条件","动词た形＋ら：如果…"),card("掴んで","つかんで","tsukande","抓住、紧握","动词（て形）","掴む的て形"),card("やろう","やろう","yarou","来做吧、会做给你看","意志形","やる的意志形，表示决心")],
"l047": [card("灰色の空","はいいろのそら","haiiro no sora","灰色的天空","名词短语","名词＋の＋名词"),card("その中で","そのなかで","sono naka de","在那之中","地点表达","名词＋の中で"),card("煌めく","きらめく","kirameku","闪耀、闪烁","动词","修饰青さ"),card("青さを","あおさを","aosa o","蓝色（作对象）","名词＋助词","を标记省略的动作对象",False)],
"l066": [card("何もかも","なにもかも","nani mo kamo","一切、所有","副词性名词","何も＋かも：所有一切"),card("君次第で","きみしだいで","kimi shidai de","取决于你","句型","名词＋次第で：取决于…"),card("僕次第さ","ぼくしだいさ","boku shidai sa","取决于我啊","句型＋终助词","名词＋次第＋さ：取决于…啊")],
}

# Refrains intentionally reuse the same fully reviewed bundles; this is an
# explicit proposal, never a silent mutation of frames.json.
REPEAT = {
 "l032":"l006", "l033":"l007", "l034":"l008", "l035":"l009", "l036":"l010", "l037":"l011",
 "l048":"l020", "l049":"l021", "l050":"l022", "l051":"l023", "l052":"l024", "l053":"l025", "l054":"l026", "l055":"l027", "l056":"l028", "l057":"l029", "l058":"l030", "l059":"l031",
 "l060":"l006", "l061":"l007", "l062":"l008", "l063":"l009", "l064":"l010", "l065":"l011",
}

def main():
    raw = FRAMES.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    ids = [f["id"] for f in data["frames"]]
    missing = [x for x in ids if x not in C and x not in REPEAT]
    if missing:
        raise RuntimeError(f"Missing complete grammar card bundle for: {missing}")
    changes = []
    for frame in data["frames"]:
        fid = frame["id"]
        source = REPEAT.get(fid, fid)
        new = copy.deepcopy(C[source])
        changes.append({
            "frameId": fid, "field": "grammarCards", "old": frame.get("grammarCards", []), "new": new,
            "confidence": 0.94 if fid not in REPEAT else 0.98,
            "evidence": ["完整重建：短卡字段固定为词条、读音、罗马音、释义/功能、词性；复句优先合并为固定搭配或活用。"],
            "changesTokenStructure": True,
        })
    proposal = {
        "schemaVersion": 3,
        "reviewRole": "grammar",
        "scope": {"frameIds": ids, "coverage": "all-japanese-lyric-frames"},
        "baseFrameSha256": hashlib.sha256(raw).hexdigest(),
        "changes": changes,
        "reviewNotes": [
            "所有61条实际歌词均有 grammarCards 新值；副歌重复行显式继承同一语义束。",
            "助词仅使用 functionZh；动词的て/で形作为活用整体，不拆成助词。",
            "grammarStructureZh 为审阅数据，卡面仅应显示 posZh。"
        ]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {len(changes)} complete changes")

if __name__ == "__main__":
    main()
