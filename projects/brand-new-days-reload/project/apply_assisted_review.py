"""Import the bounded multi-agent review proposal into the current draft."""
import json
from pathlib import Path

ROOT, OUT = Path(__file__).parent, Path(__file__).parent.parent / "deliverables"
data = json.loads((ROOT / "frames.review.json").read_text(encoding="utf-8"))

def c(token, reading, romaji, meaning, pos, source=None):
    item={"token":token,"reading":reading,"romaji":romaji,"posZh":pos,"render":True}
    if pos.endswith("助词") or "助词" in pos: item["functionZh"] = meaning
    else: item["zhMeaning"] = meaning
    if source: item["sourceWord"] = source
    return item

def setf(num, translation, *cards):
    frame=data["frames"][num-1]
    frame["caption"]["translationZh"] = translation
    frame["grammarCards"] = list(cards)
    frame["analysisStatus"] = "assisted-review-needs-human-confirmation"
    return frame

# l001-l016: semantics role
setf(1,"晨光唤醒了梦。",c("梦","ゆめ","yume","梦","名词"),c("を","を","wo","动作对象","助词"),c("醒ます","さます","samasu","唤醒","动词"),c("朝","あさ","asa","早晨","名词"),c("の","の","no","所属／修饰","助词"),c("光","ひかり","hikari","光芒","名词"))
setf(2,"再次照亮这个世界。",c("また","また","mata","再次","副词"),c("照らし出す","てらしだす","terashidasu","照亮；映照出来","动词"))
setf(3,"这个世界。",c("この","この","kono","这个","连体词"),c("世界","せかい","sekai","世界","名词"))
setf(4,"只带着中断的约定，独自背负着。",c("途切れた","とぎれた","togireta","中断了的","动词（过去形）"),c("約束","やくそく","yakusoku","约定","名词"),c("だけ","だけ","dake","限定“只”","副助词"),c("独り","ひとり","hitori","独自一人","名词／副词"),c("かかえて","かかえて","kakaete","背负着；抱着","动词（て形）"))
setf(5,"只追逐着眼睑后的昨日。",c("瞼","まぶた","mabuta","眼睑","名词"),c("の","の","no","所属／修饰","助词"),c("昨日","きのう","kinou","昨天；昨日的景象","名词"),c("だけ","だけ","dake","限定“只”","副助词"))
setf(6,"追逐了。",c("追いかけた","おいかけた","oikaketa","追逐了","动词（过去形）"))
setf(7,"我竟忘记了。",c("忘れてた","わすれてた","wasureteta","曾经忘记了","动词（ている过去缩约）"),c("よ","よ","yo","句末强调／告知","终助词"))
setf(8,"如此澄澈的天蓝色。",c("こんなに","こんなに","konnani","如此地；这么","副词"),c("透き通った","すきとおった","sukitootta","澄澈的；通透的","动词（过去形／连体）"),c("スカイブルー","スカイブルー","sukaiburuu","天蓝色","名词（片假外来语）","sky blue"))
setf(9,"一定是你给予我的真实感受之光辉。",c("きっと","きっと","kitto","一定","副词"),c("キミ","きみ","kimi","你","代词"),c("が","が","ga","主语标记","格助词"),c("くれた","くれた","kureta","（你）给了我","动词（过去形）"),c("輝き","かがやき","kagayaki","光辉；闪耀","名词"))
setf(10,"终有一天。",c("いつか","いつか","itsuka","总有一天；某一天","副词"))
setf(11,"即使被相牵双手的力度所伤。",c("つないだ","つないだ","tsunaida","牵起了；相连的","动词（过去形）"),c("手","て","te","手","名词"),c("の","の","no","所属／修饰","助词"),c("強さ","つよさ","tsuyosa","强度；力量","名词（形容词名词化）"),c("に","に","ni","受影响的对象／原因","格助词"),c("傷ついても","きずついても","kizutsuittemo","即使受伤也……","动词（て形＋让步も）"))
setf(12,"绝对不会放开哦。",c("絶対","ぜったい","zettai","绝对","副词"),c("はなさない","はなさない","hanasanai","不放开","动词（否定形）"),c("よ","よ","yo","句末强调／告知","终助词"))
setf(13,"亲爱的朋友们，就这样一直走下去。",c("このまま","このまま","konomama","就这样；保持现状","名词性短语"),c("ずっと","ずっと","zutto","一直","副词"))
setf(14,"迷茫的岁月里，曾多少次仰望同一轮月亮呢。",c("同じ","おなじ","onaji","相同的","连体词"),c("月","つき","tsuki","月亮","名词"),c("を","を","wo","动作对象","格助词"),c("幾つ","いくつ","ikutsu","多少个；几次","疑问代词"),c("見上げた","みあげた","miageta","仰望了","动词（过去形）"),c("だろう","だろう","darou","推测／自问感叹","助动词"))
setf(15,"我们也曾跨越同样的离别吧。",c("同じ","おなじ","onaji","相同的","连体词"),c("さよなら","さよなら","sayonara","告别；离别","名词"),c("を","を","wo","动作对象","格助词"))
setf(16,"跨越了吧。",c("越えた","こえた","koeta","跨越了","动词（过去形）"),c("だろう","だろう","darou","推测／自问感叹","助动词"))

# l017-l032: grammar role
setf(17,"痛苦所赠予的宝石。",c("痛み","いたみ","itami","痛苦","名词"),c("が","が","ga","主语标记","助词"),c("くれる","くれる","kureru","赠予／带来","动词"),c("宝石","ほうせき","houseki","宝石","名词"))
setf(18,"明明应该早就知道的，却……",c("知ってた","しってた","shiteta","已经知道","动词（口语缩约）"),c("はず","はず","hazu","理应；按理","形式名词"),c("なのに","なのに","nanoni","明明……却……","接续助词"))
setf(19,"只有失去的光芒。",c("なくした","なくした","nakushita","失去的","动词（过去形）"),c("光","ひかり","hikari","光芒","名词"),c("だけ","だけ","dake","限定范围：只有","副助词"))
setf(20,"一直数着。",c("数えてた","かぞえてた","kazoeteta","一直数着","动词（口语缩约）"))
setf(21,"回过神来便，你看。",c("気付けば","きづけば","kizukeba","回过神来便；一察觉就","动词（ば形）"),c("ほら","ほら","hora","你看；瞧","感叹词"))
setf(22,"隔着窗，耀眼的天蓝色。",c("窓越し","まどごし","madogoshi","隔着窗；透过窗","名词"),c("眩しい","まぶしい","mabushii","耀眼的","形容词"),c("スカイブルー","スカイブルー","sukaiburuu","天蓝色；蔚蓝","名词（片假外来语）","sky blue"))
setf(23,"明天的门一定仍会向我敞开。",c("きっと","きっと","kitto","一定","副词"),c("明日","あす","asu","明天","名词"),c("の","の","no","所属／修饰","助词"),c("ドア","ドア","doa","门","名词（片假外来语）","door"),c("が","が","ga","主语标记","助词"),c("開く","ひらく","hiraku","打开；敞开","动词"),c("よ","よ","yo","句末断定、提醒","终助词"))
setf(24,"总有一天，流转的时光……",c("いつか","いつか","itsuka","总有一天","副词"),c("巡る","めぐる","meguru","流转","动词"),c("時","とき","toki","时光；时候","名词"),c("が","が","ga","主语标记","助词"))
setf(25,"即使一切都改变了。",c("全て","すべて","subete","一切","名词"),c("を","を","wo","动作对象","助词"),c("変えてしまっても","かえてしまっても","kaeteshimattemo","即使全都改变了","动词（完成／让步）"))
setf(26,"我绝不会失去你。",c("絶対","ぜったい","zettai","绝对","副词"),c("なくさない","なくさない","nakusanai","不弄丢；不失去","动词（否定形）"),c("よ","よ","yo","句末断定、提醒","终助词"),c("キミ","きみ","kimi","你","代词"),c("を","を","wo","动作对象","助词"))
setf(27,"唤醒梦境的清晨阳光。",*data["frames"][0]["grammarCards"])
setf(28,"然后开始闪耀。",c("そして","そして","soshite","然后；而后","连词"),c("輝き出す","かがやきだす","kagayakidasu","开始闪耀","动词（连用形＋出す）"))
setf(29,"这个世界。",c("この","この","kono","这个","连体词"),c("世界","せかい","sekai","世界","名词"))
setf(30,"因呼唤活着的意义而疲惫。",c("生きる","いきる","ikiru","活着；生存","动词"),c("意味","いみ","imi","意义","名词"),c("を","を","wo","动作对象","助词"),c("呼び疲れ","よびつかれ","yobitsukare","因呼唤而疲惫","动词"))
setf(31,"也有垂下头的日子。",c("俯く","うつむく","utsumuku","低下头；垂头","动词"),c("日","ひ","hi","日子","名词"),c("も","も","mo","追加：也／甚至","副助词"),c("ある","ある","aru","有；存在","动词"))
setf(32,"即便如此，在心中……",c("それでも","それでも","soredemo","即便如此","连词"),c("心","こころ","kokoro","心中","名词"),c("には","には","niwa","存在地点＋提示对比","助词组合"))

# l033-l048: timing/reading role
setf(33,"即便如此，心中仍有你的笑容。",c("キミ","きみ","kimi","你","代词"),c("の","の","no","所属／修饰","助词"),c("笑顔","えがお","egao","笑容","名词"))
setf(34,"我竟忘记了。",*data["frames"][6]["grammarCards"])
setf(35,"如此澄澈的天蓝色。",*data["frames"][7]["grammarCards"])
setf(36,"一定是你给予我的真实感受之光辉。",*data["frames"][8]["grammarCards"])
setf(37,"因为从梦中醒来，所以才能相遇。",c("夢","ゆめ","yume","梦","名词"),c("が","が","ga","主语标记","助词"),c("醒める","さめる","sameru","醒来；梦醒","动词"),c("から","から","kara","表示原因：因为","接续助词"),c("出会える","であえる","deaeru","能够相遇","动词（可能形）"))
setf(38,"向崭新的明天。",c("新しい","あたらしい","atarashii","新的","形容词"),c("明日","あす","asu","明天","名词"),c("に","に","ni","目标／去向","格助词"))
setf(39,"我绝对相信着。",c("絶対","ぜったい","zettai","绝对","副词"),c("信じてる","しんじてる","shinjiteru","相信着","动词（口语缩约）"),c("よ","よ","yo","加强告知／断言","终助词"))
setf(40,"你的信念，无论何时都始终如一。",c("いつでも","いつでも","itsudemo","无论何时；总是","副词"),c("ずっと","ずっと","zutto","一直；始终","副词"))
setf(41,"回过神来便，你看。",*data["frames"][20]["grammarCards"])
setf(42,"隔着窗，耀眼的天蓝色。",*data["frames"][21]["grammarCards"])
setf(43,"明日的大门一定一直敞开着。",c("きっと","きっと","kitto","一定","副词"),c("明日","あす","asu","明天","名词"),c("の","の","no","所属／修饰","助词"),c("ドア","ドア","doa","门","名词（片假外来语）","door"),c("は","は","wa","主题提示","助词"),c("あいてた","あいてた","aiteta","一直开着；敞开着","动词（口语缩约）"))
setf(44,"在春风中听得见毕业的歌声。",c("春","はる","haru","春天","名词"),c("の","の","no","所属／修饰","助词"),c("風","かぜ","kaze","风","名词"),c("に","に","ni","现象发生的场所／载体","格助词"),c("聴こえる","きこえる","kikoeru","听得见；传入耳中","动词"))
setf(45,"从今天开始的真实岁月。",c("今日","きょう","kyou","今天","名词"),c("から","から","kara","从；起自","格助词"),c("の","の","no","连接并修饰后项","格助词"))
setf(46,"前往与你相遇的未来。",c("キミ","きみ","kimi","你","代词"),c("と","と","to","和；与","格助词"),c("出会う","であう","deau","相遇","动词"),c("未来","あした","ashita","未来；明日（歌词特殊读法）","名词"),c("へ","へ","e","移动方向","格助词"))
setf(47,"从这里开启全新的奇迹。",c("新しい","あたらしい","atarashii","新的","形容词"),c("奇跡","きせき","kiseki","奇迹","名词"),c("を","を","wo","动作对象","格助词"),c("ここ","ここ","koko","这里","代词"),c("から","から","kara","从；起自","格助词"),c("始める","はじめる","hajimeru","开始；开启","动词"))
setf(48,"在那闪耀之地，呐，还想再一次和你一起……",c("ねえ","ねえ","nee","呐","感叹词"),c("もう一度","もういちど","mou ichido","再一次","副词性短语"),c("キミ","きみ","kimi","你","代词"),c("と","と","to","和；与","格助词"))

data["reviewStatus"]="assisted-review-needs-human-confirmation"
data["assistedReviewSources"]=["QQ Music qm/qmRoma/qmts", "three bounded subagent passes", "authoritative dictionary/grammar lookups when unresolved"]
(ROOT / "frames.assisted.review.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

lines=["# Brand New Days -Reload-｜智能审核词卡", "", "状态：已由三组角色审核，仍待人工确认。英文仅作歌词展示，不生成词卡。", ""]
for frame in data["frames"]:
    lines += [f"## {frame['id']}　{frame['startMs']/1000:06.2f}",f"日文：{frame['caption']['japanese']}",f"暂定中文：{frame['caption']['translationZh']}","", "待核词卡："]
    for item in frame["grammarCards"]:
        meaning=item.get("functionZh",item.get("zhMeaning",""))
        lines += [f"- `{item['token']}`｜{item['reading']}｜{item['romaji']}",f"  - 暂定：{meaning}",f"  - 词性：{item['posZh']}"]
    lines.append("")
(OUT / "brand-new-days-assisted-review.md").write_text("\n".join(lines),encoding="utf-8")
(ROOT / "review-import-log.md").write_text("# Assisted review import\n\nImported bounded proposals for l001–l048. Repeated card inheritance: l027←l001; l034←l007; l035←l008; l036←l009; l041←l021; l042←l022.\n",encoding="utf-8")
print("Imported assisted review for",len(data["frames"]),"frames")
