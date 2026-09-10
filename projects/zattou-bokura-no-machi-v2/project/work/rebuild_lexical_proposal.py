import json
import hashlib
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\zattou-bokura-no-machi-v2")
frames_path = ROOT / "project" / "frames.json"
frames_bytes = frames_path.read_bytes()
frames = json.loads(frames_bytes)
base_sha = hashlib.sha256(frames_bytes).hexdigest()

def c(token, reading, romaji, meaning=None, pos="名词", function=None):
    assert bool(meaning) ^ bool(function), token
    return {
        "token": token, "reading": reading, "romaji": romaji,
        **({"zhMeaning": meaning} if meaning else {"functionZh": function}),
        "posZh": pos, "grammarStructureZh": pos,
        "render": True, "showJlpt": False, "reviewRequired": True,
    }

K = {
"やり残した鼓動がこの夜を覆って": [c("やり残した","やりのこした","yarinokoshita","留下未完成的","复合动词（た形）"),c("鼓動","こどう","kodou","心跳","名词"),c("が","が","ga",function="提示主语",pos="助词"),c("この","この","kono","这个","连体词"),c("夜","よる","yoru","夜晚","名词"),c("を","を","o",function="提示动作对象",pos="助词"),c("覆って","おおって","ootte","覆盖、笼罩","动词（て形）")],
"僕らを包んで 粉々になる前に": [c("僕ら","ぼくら","bokura","我们","代词"),c("を","を","o",function="提示动作对象",pos="助词"),c("包んで","つつんで","tsutsunde","包裹着","动词（て形）"),c("粉々に","こなごなに","konagona ni","变得粉碎","副词性名词＋に"),c("なる","なる","naru","变成","动词"),c("前に","まえに","mae ni","在……之前","时间表达")],
"頼りなくてもいい その手を": [c("頼りなくてもいい","たよりなくてもいい","tayorinakutemo ii","即使不可靠也可以","句型"),c("その","その","sono","那个","连体词"),c("手","て","te","手","名词"),c("を","を","o",function="提示动作对象",pos="助词")],
"この手は自分自身のものさ": [c("この","この","kono","这","连体词"),c("手","て","te","手","名词"),c("は","は","wa",function="提示主题",pos="助词"),c("自分自身","じぶんじしん","jibun jishin","自己本身","代词"),c("もの","もの","mono","东西；所属之物","名词"),c("さ","さ","sa",function="加强断定语气",pos="终助词")],
"変わらないはずはないよ": [c("変わらない","かわらない","kawaranai","不会改变","动词（ない形）"),c("はずはない","はずはない","hazu wa nai","不可能……","句型"),c("よ","よ","yo",function="告知、强调",pos="终助词")],
"手を伸ばして": [c("手","て","te","手","名词"),c("を","を","o",function="提示动作对象",pos="助词"),c("伸ばして","のばして","nobashite","伸出","动词（て形）")],
"雑踏の中で声無き声で泣いている": [c("雑踏","ざっとう","zattou","人潮；拥挤街头","名词"),c("の中で","のなかで","no naka de","在……之中","表达"),c("声無き","こえなき","koenaki","无声的","连体表达"),c("声","こえ","koe","声音","名词"),c("で","で","de",function="表示方式、状态",pos="助词"),c("泣いている","ないている","naite iru","正在哭泣","动词持续形")],
"足跡が今 誰かの声を消した朝": [c("足跡","あしあと","ashiato","足迹","名词"),c("が","が","ga",function="提示主语",pos="助词"),c("今","いま","ima","现在；此刻","名词"),c("誰か","だれか","dareka","某个人","代词"),c("の","の","no",function="表示所属、修饰",pos="助词"),c("声","こえ","koe","声音","名词"),c("消した","けした","keshita","消除了","动词（た形）"),c("朝","あさ","asa","清晨","名词")],
"いつになっても枯れることのない": [c("いつになっても","いつになっても","itsu ni natte mo","无论何时都……","句型"),c("枯れる","かれる","kareru","枯萎","动词"),c("ことのない","ことのない","koto no nai","没有……的；从不……","表达")],
"腐敗した街の泥水が冷たい": [c("腐敗した","ふはいした","fuhai shita","腐败的","名词＋する（た形）"),c("街","まち","machi","城市；街道","名词"),c("泥水","どろみず","doromizu","泥水","名词"),c("が","が","ga",function="提示主语",pos="助词"),c("冷たい","つめたい","tsumetai","冰冷的","い形容词")],
"何にも変わらない世界で": [c("何にも","なんにも","nan ni mo","什么都不……","代词＋助词"),c("変わらない","かわらない","kawaranai","不改变","动词（ない形）"),c("世界","せかい","sekai","世界","名词"),c("で","で","de",function="表示动作发生的场所",pos="助词")],
"今日だって生きてゆくんだ": [c("今日","きょう","kyou","今天","名词"),c("だって","だって","datte",function="表示即使、也仍然",pos="副助词"),c("生きてゆく","いきてゆく","ikite yuku","活下去","动词表达"),c("んだ","んだ","nda",function="说明、强调语气",pos="终助词")],
"くだらないけど 仕方ないでしょ": [c("くだらない","くだらない","kudaranai","无聊的；没意义的","い形容词"),c("けど","けど","kedo",function="表示转折：但是、不过",pos="接续助词"),c("仕方ない","しかたない","shikata nai","无可奈何","固定表达"),c("でしょ","でしょ","desho",function="寻求认同、确认",pos="终助词")],
"僕らはもう 歩き始めたんだ": [c("僕ら","ぼくら","bokura","我们","代词"),c("は","は","wa",function="提示主题",pos="助词"),c("もう","もう","mou","已经","副词"),c("歩き始めた","あるきはじめた","aruki hajimeta","开始迈步","复合动词（た形）"),c("んだ","んだ","nda",function="说明、强调语气",pos="终助词")],
"嘘みたいな 馬鹿みたいな": [c("嘘みたいな","うそみたいな","uso mitai na","像谎言一样的；难以置信的","比况表达"),c("馬鹿みたいな","ばかみたいな","baka mitai na","像傻瓜一样的","比况表达")],
"どうしようもない僕らの街": [c("どうしようもない","どうしようもない","doushiyou mo nai","无可奈何的；无药可救的","固定表达"),c("僕ら","ぼくら","bokura","我们","代词"),c("の","の","no",function="表示所属、修饰",pos="助词"),c("街","まち","machi","城市；街道","名词")],
"それでも": [c("それでも","それでも","sore demo","即便如此","接续词")],
"この眼で確かに見えたんだ": [c("この","この","kono","这","连体词"),c("眼","め","me","眼睛","名词"),c("で","で","de",function="表示手段、方式",pos="助词"),c("確かに","たしかに","tashika ni","确实地","副词"),c("見えた","みえた","mieta","看得见了","动词（た形）"),c("んだ","んだ","nda",function="说明、强调语气",pos="终助词")],
"この手で確かに触れたんだ": [c("この","この","kono","这","连体词"),c("手","て","te","手","名词"),c("で","で","de",function="表示手段、方式",pos="助词"),c("確かに","たしかに","tashika ni","确实地","副词"),c("触れた","ふれた","fureta","触碰到了","动词（た形）"),c("んだ","んだ","nda",function="说明、强调语气",pos="终助词")],
"ねえ ほら ほら": [c("ねえ","ねえ","nee",function="呼唤、引起注意",pos="感叹词"),c("ほら","ほら","hora",function="提醒对方看、听或注意",pos="感叹词")],
"ほらまた吹いた 馬鹿みたいだ": [c("ほら","ほら","hora",function="提醒对方看、听或注意",pos="感叹词"),c("また","また","mata","又；再次","副词"),c("吹いた","ふいた","fuita","吹起了","动词（た形）"),c("馬鹿みたいだ","ばかみたいだ","baka mitai da","像傻瓜一样","比况表达")],
"どうしようもない闇を照らせ": [c("どうしようもない","どうしようもない","doushiyou mo nai","无可奈何的；无药可救的","固定表达"),c("闇","やみ","yami","黑暗","名词"),c("を","を","o",function="提示动作对象",pos="助词"),c("照らせ","てらせ","terase","照亮吧","动词命令形")],
"夢じゃない": [c("夢","ゆめ","yume","梦","名词"),c("じゃない","じゃない","ja nai","不是……","否定表达")],
"どうせ終わってる街だって": [c("どうせ","どうせ","douse","反正；横竖","副词"),c("終わってる","おわってる","owatteru","已经结束了","动词持续形"),c("街","まち","machi","城市；街道","名词"),c("だって","だって","datte",function="表示即使、也仍然",pos="副助词")],
"諦めたって変わんないぜ": [c("諦めたって","あきらめたって","akirametatte","即使放弃也……","让步表达"),c("変わんない","かわんない","kawannai","不会改变","口语否定"),c("ぜ","ぜ","ze",function="加强断定、带有强烈语气",pos="终助词")],
"ああ まだ まだ まだ": [c("ああ","ああ","aa",function="感叹、呼应情绪",pos="感叹词"),c("まだ","まだ","mada","还；仍然","副词")],
"永遠の中で 迷わない為の温もり": [c("永遠","えいえん","eien","永远","名词"),c("の中で","のなかで","no naka de","在……之中","表达"),c("迷わない","まよわない","mayowanai","不迷失","动词（ない形）"),c("為の","ための","tame no","为了……的","表达"),c("温もり","ぬくもり","nukumori","温暖","名词")],
"軽薄な君に": [c("軽薄な","けいはくな","keihaku na","轻率的；浮薄的","な形容词"),c("君","きみ","kimi","你","代词"),c("に","に","ni",function="表示对象、方向",pos="助词")],
"届くことなく散ってゆく": [c("届く","とどく","todoku","传达到；到达","动词"),c("ことなく","ことなく","koto naku","不……便……","书面表达"),c("散ってゆく","ちってゆく","chitte yuku","渐渐消散","动词表达")],
"想像通り？ そんなはずはない": [c("想像通り","そうぞうどおり","souzou doori","如想象一般","名词＋通り"),c("そんな","そんな","sonna","那样的","连体词"),c("はずはない","はずはない","hazu wa nai","不可能……","句型")],
"逃げりゃいいでしょ？": [c("逃げりゃ","にげりゃ","nigerya","如果逃避的话","口语假定形"),c("いい","いい","ii","可以；好","い形容词"),c("でしょ","でしょ","desho",function="寻求认同、确认",pos="终助词")],
"簡単に言わないで": [c("簡単に","かんたんに","kantan ni","轻易地；简单地","な形容词副词形"),c("言わないで","いわないで","iwanai de","不要说","禁止表达")],
"いつも通りの世界を": [c("いつも通り","いつもどおり","itsumo doori","一如往常","副词性名词"),c("世界","せかい","sekai","世界","名词"),c("を","を","o",function="提示动作对象",pos="助词")],
"今日だって駆けてゆくんだ": [c("今日","きょう","kyou","今天","名词"),c("だって","だって","datte",function="表示即使、也仍然",pos="副助词"),c("駆けてゆく","かけてゆく","kakete yuku","奔跑着前行","动词表达"),c("んだ","んだ","nda",function="说明、强调语气",pos="终助词")],
"滑り落ちたら 掴んでやろう": [c("滑り落ちたら","すべりおちたら","suberi ochitara","如果滑落的话","复合动词假定形"),c("掴んで","つかんで","tsukande","抓住","动词（て形）"),c("やろう","やろう","yarou",function="表示替他人做某事的强烈意志",pos="补助动词")],
"灰色の空 その中で煌めく青さを": [c("灰色","はいいろ","haiiro","灰色","名词"),c("空","そら","sora","天空","名词"),c("その中で","そのなかで","sono naka de","在那之中","表达"),c("煌めく","きらめく","kirameku","闪耀","动词"),c("青さ","あおさ","aosa","蓝色；蓝意","名词"),c("を","を","o",function="提示动作对象",pos="助词")],
"何もかも君次第で 僕次第さ": [c("何もかも","なにもかも","nani mo kamo","一切；全部","代词"),c("君","きみ","kimi","你","代词"),c("次第で","しだいで","shidai de","取决于……","名词＋で"),c("僕","ぼく","boku","我","代词"),c("さ","さ","sa",function="加强断定语气",pos="终助词")],
}

# Reuse only the already-audited kanji-run readings, rebased to current frames.
old = json.loads((ROOT / "project" / "proposals" / "lexical.json.superseded-full-card-rebuild").read_text(encoding="utf-8"))
old_furi = {x["frameId"]: x["new"] for x in old["changes"] if x["field"] == "caption.furigana"}

changes=[]
for frame in frames["frames"]:
    fid, text = frame["id"], frame["caption"]["japanese"]
    if text not in K:
        raise KeyError(text)
    changes.append({"frameId":fid,"field":"caption.furigana","old":frame["caption"].get("furigana",[]),"new":old_furi.get(fid,[]),"confidence":0.99,"evidence":["QMRoma timing cross-check; kanji-only furigana rule"],"changesTokenStructure":False})
    changes.append({"frameId":fid,"field":"grammarCards","old":frame.get("grammarCards",[]),"new":K[text],"confidence":0.93,"evidence":["Full-line semantic reading aligned to QMTS Chinese translation","Card schema: token｜reading｜romaji｜meaning/function｜short POS"],"changesTokenStructure":True})

out={"schemaVersion":3,"reviewRole":"lexical","scope":{"frameIds":[f["id"] for f in frames["frames"]]},"baseFrameSha256":base_sha,"changes":changes,"reviewNotes":{"coverage":"61/61 lyric frames","loanwordPolicy":"No true katakana loanword tokens occur in these 61 Japanese lyric frames; therefore no sourceWord entries are proposed.","cardDisplay":"grammarStructureZh is intentionally the short POS display line; exactly one of zhMeaning/functionZh is set per card."}}
(ROOT / "project" / "proposals" / "lexical.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"frames":len(frames["frames"]),"changes":len(changes),"sha":base_sha,"out":str(ROOT / "project" / "proposals" / "lexical.json")},ensure_ascii=False))
