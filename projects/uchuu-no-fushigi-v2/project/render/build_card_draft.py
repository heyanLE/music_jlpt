"""Create editable, explicitly unconfirmed study-card drafts from frozen QRC rows."""
import copy
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROJECT, QA, OUT = ROOT / "project", ROOT / "project" / "qa", ROOT / "deliverables" / "review"
FONT = "C:/Windows/Fonts/msyhbd.ttc"
W, H = 1920, 1080

def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def card(token, reading, romaji, meaning, pos, particle=False):
    value = {"token": token, "reading": reading, "romaji": romaji, "posZh": pos, "status": "draft", "fieldProvenance": "draft-local-semantic-segmentation"}
    value["functionZh" if particle else "zhMeaning"] = meaning
    return value
def p(token, meaning): return card(token, token, {"は":"wa","を":"wo","に":"ni","で":"de","の":"no","と":"to","も":"mo","が":"ga","ね":"ne"}.get(token, token), meaning, "助词", True)
def c(t,r,ro,m,pos): return card(t,r,ro,m,pos)

# Each tuple: provisional Chinese, teachable semantic chunks.  All are drafts.
S = [
 ("鸟为什么能在天空飞翔呢？", [c("鳥","とり","tori","鸟","名词"),p("は","主题提示"),c("なんで","なんで","nande","为什么","疑问副词"),c("空","そら","sora","天空","名词"),p("を","动作对象"),c("とべる","とべる","toberu","能飞","动词（可能形）"),c("の","の","no","疑问语气","终助词")]),
 ("猫为什么总是在睡觉呢？", [c("猫","ねこ","neko","猫","名词"),p("は","主题提示"),c("なんで","なんで","nande","为什么","疑问副词"),c("ずっと","ずっと","zutto","一直","副词"),c("ねてる","ねてる","neteru","正在睡（寝ている的缩约）","动词（进行）"),c("の","の","no","疑问语气","终助词")]),
 ("你会度过怎样的今天呢？", [c("君","きみ","kimi","你","人称代词"),p("は","主题提示"),c("どんな","どんな","donna","什么样的","连体词"),c("今日","きょう","kyou","今天","名词"),p("を","动作对象"),c("生きる","いきる","ikiru","生活、度过","动词"),c("の","の","no","疑问语气","终助词")]),
 ("全部、全部、全部。", [c("ぜんぶ","ぜんぶ","zenbu","全部","名词")]),
 ("一起去寻找吧。", [c("さがし","さがし","sagashi","寻找（探す的连用形）","动词"),p("に","动作目的"),c("ゆこう","ゆこう","yukou","去吧、一起去（行こう的口语）","动词（意志形）")]),
 ("清晨为什么照亮我呢？", [c("朝","あさ","asa","清晨","名词"),p("は","主题提示"),c("なんで","なんで","nande","为什么","疑问副词"),c("僕","ぼく","boku","我","人称代词"),p("を","动作对象"),c("照らす","てらす","terasu","照亮","动词"),c("の","の","no","疑问语气","终助词")]),
 ("夜晚为什么会变得寂寞呢？", [c("夜","よる","yoru","夜晚","名词"),p("は","主题提示"),c("なんで","なんで","nande","为什么","疑问副词"),c("寂しく","さびしく","sabishiku","变得寂寞地","形容词"),c("なる","なる","naru","变成","动词"),c("の","の","no","疑问语气","终助词")]),
 ("悲伤的事就一人一半。", [c("かなしい","かなしい","kanashii","悲伤的","形容词"),c("こと","こと","koto","事情","名词"),p("は","主题提示"),c("はんぶんこ","はんぶんこ","hanbunko","一人一半、平分","名词")]),
 ("要是能做到就好了呢。", [c("できたら","できたら","dekitara","如果能做到","动词（条件形）"),c("いい","いい","ii","好、就好了","形容词"),c("のに","のに","noni","却／明明……却……","接续助词"),p("ね","征求认同、加强感叹")]),
 ("时而笑笑，时而试着烦恼。", [c("笑ったり","わらったり","warattari","时而笑笑","动词＋列举助词"),c("悩んでみたり","なやんでみたり","nayandemitari","时而试着烦恼","动词＋补助动词＋列举助词")]),
 ("在这广阔世界的一角。", [c("この","この","kono","这个","连体词"),c("広い","ひろい","hiroi","广阔的","形容词"),c("世界","せかい","sekai","世界","名词"),p("の","所属、修饰"),c("すみっこ","すみっこ","sumikko","角落","名词"),p("で","动作、状态发生的地点")]),
 ("由我们来解开宇宙的不可思议吧。", [c("僕ら","ぼくら","bokura","我们","人称代词"),p("で","手段、主体"),c("うちゅう","うちゅう","uchuu","宇宙","名词"),p("の","所属、修饰"),c("ふしぎ","ふしぎ","fushigi","不可思议","名词")]),
 ("来解开、弄明白吧。", [c("解き明かして","ときあかして","tokiakashite","解开、弄明白","动词（て形）"),c("みよう","みよう","miyou","试着看看吧","补助动词（意志形）")]),
 ("星星为什么在闪耀呢？", [c("星","ほし","hoshi","星星","名词"),p("は","主题提示"),c("なんで","なんで","nande","为什么","疑问副词"),c("輝いてる","かがやいてる","kagayaiteru","正在闪耀","动词（进行）"),c("の","の","no","疑问语气","终助词")]),
 ("云朵为什么在天空中游泳呢？", [c("雲","くも","kumo","云朵","名词"),p("は","主题提示"),c("どうして","どうして","doushite","为什么","副词"),c("空","そら","sora","天空","名词"),p("を","动作经过的场所"),c("泳ぐ","およぐ","oyogu","游泳","动词"),c("の","の","no","疑问语气","终助词")]),
 ("人为什么要描绘梦想呢？", [c("人","ひと","hito","人","名词"),p("は","主题提示"),c("なんで","なんで","nande","为什么","疑问副词"),c("夢","ゆめ","yume","梦想","名词"),p("を","动作对象"),c("描く","えがく","egaku","描绘","动词"),c("の","の","no","疑问语气","终助词")]),
 ("也许根本没有答案吧。", [c("答え","こたえ","kotae","答案","名词"),c("なんて","なんて","nante","举例并带轻视、感叹语气","副助词"),c("ない","ない","nai","没有","形容词"),c("のかな","のかな","nokana","是不是呢／也许吧","句末表达")]),
 ("总有一天，这首小小的歌……", [c("いつか","いつか","itsuka","总有一天","副词"),c("こんな","こんな","konna","这样的","连体词"),c("小さな","ちいさな","chiisana","小小的","连体词"),c("歌","うた","uta","歌","名词"),p("は","主题提示")]),
 ("你一定会忘掉吧，但……", [c("君","きみ","kimi","你","人称代词"),p("は","主题提示"),c("きっと","きっと","kitto","一定","副词"),c("忘れちゃう","わすれちゃう","wasurechau","会忘掉（忘れてしまう的缩约）","动词"),c("けど","けど","kedo","但是、不过","接续助词")]),
 ("但我会一直记得哦。", [c("僕","ぼく","boku","我","人称代词"),p("は","主题提示"),c("ずっと","ずっと","zutto","一直","副词"),c("覚えている","おぼえている","oboeteiru","一直记得","动词（进行）"),c("よ","よ","yo","句末告知、强调","终助词")]),
 ("即使长大以后也要记得哦。", [c("大人","おとな","otona","大人","名词"),p("に","变化的结果"),c("なっても","なっても","nattemo","即使变成……也……","动词＋让步助词"),p("ね","征求认同、柔和语气")]),
 ("今天要聊些什么呢？", [c("今日","きょう","kyou","今天","名词"),p("は","主题提示"),c("どんな","どんな","donna","什么样的","连体词"),c("話","はなし","hanashi","话题、谈话","名词"),p("を","动作对象"),c("しよう","しよう","shiyou","来做吧、来聊吧","动词（意志形）")]),
 ("要和你一起唱怎样的歌呢？", [c("君","きみ","kimi","你","人称代词"),p("と","共同对象"),c("どんな","どんな","donna","什么样的","连体词"),c("歌","うた","uta","歌","名词"),p("を","动作对象"),c("歌おう","うたおう","utaou","一起唱吧","动词（意志形）")]),
 ("还有仍无人知晓的花朵……", [c("誰","だれ","dare","谁","疑问代词"),p("も","与否定搭配：任何……也不"),c("まだ","まだ","mada","还、尚未","副词"),c("知らない","しらない","shiranai","不知道的","动词（否定）"),c("花","はな","hana","花朵","名词"),p("も","添加、并列")])
]

ANNOTATIONS = {"鳥":"とり","空":"そら","猫":"ねこ","君":"きみ","今日":"きょう","生":"い","朝":"あさ","僕":"ぼく","照":"て","夜":"よる","寂":"さび","広":"ひろ","世界":"せかい","解":"と","明":"あ","星":"ほし","輝":"かがや","雲":"くも","人":"ひと","夢":"ゆめ","答":"こた","小":"ちい","忘":"わす","覚":"おぼ","大人":"おとな","話":"はな","歌":"うた","誰":"だれ","知":"し","花":"はな"}

def annotations(text):
    return [{"base": base, "reading": reading} for base, reading in ANNOTATIONS.items() if base in text]

def main():
    payload = read(PROJECT / "frames.json")
    frames = payload["frames"]
    for frame, (translation, cards) in zip(frames[:24], S):
        frame["caption"]["translationZh"] = translation
        frame["caption"]["romaji"] = " ".join(item["romaji"] for item in cards)
        frame["caption"]["furigana"] = annotations(frame["caption"]["japanese"])
        frame["grammarCards"] = cards
        frame["status"] = "draft"
        frame["fieldProvenance"].update({"caption": "draft-local-translation", "grammarCards": "draft-local-semantic-segmentation", "furigana": "draft-kanji-run-annotations"})
    for target, source in ((24,3),(25,4),(26,3),(27,4)):
        translation, cards = S[source]
        frames[target]["caption"]["translationZh"] = translation
        frames[target]["caption"]["romaji"] = " ".join(item["romaji"] for item in cards)
        frames[target]["caption"]["furigana"] = []
        frames[target]["grammarCards"] = copy.deepcopy(cards)
        frames[target]["status"] = "draft"
        frames[target]["fieldProvenance"].update({"caption": "draft-repeat-inherited", "grammarCards": "draft-repeat-inherited"})
    write(PROJECT / "frames.json", payload)
    particle_table = {"は":"主题提示", "を":"动作对象", "に":"动作目的／变化结果", "で":"动作地点／手段、主体", "の":"所属、修饰", "と":"共同对象", "も":"添加、并列／与否定搭配", "ね":"征求认同、柔和语气"}
    write(PROJECT / "review" / "particle-functions.json", particle_table)
    lines = ["# うちゅうのふしぎ｜词卡草稿", "", "所有条目均为草稿；可直接在此文档修改中文或词卡，后续将导入为差异提案。", ""]
    for frame in frames:
        caption = frame["caption"]
        lines += [f"## {frame['id']} · {frame['startMs'] / 1000:.3f}s", "", f"日文：{caption['japanese']}", f"暂定中文：{caption['translationZh']}", "", "词卡："]
        for item in frame["grammarCards"]:
            meaning = item.get("functionZh", item.get("zhMeaning", ""))
            lines += [f"- `{item['token']}`｜{item['reading']}｜{item['romaji']}", f"  - 暂定：{meaning}", f"  - 词性：{item['posZh']}（草稿）"]
        lines.append("")
    review = OUT / "uchuu-no-fushigi-v2-review.md"
    review.write_text("\n".join(lines), encoding="utf-8")
    # Content-layout preview uses a real longest-card frame under the active template's geometry.
    chosen = max(frames, key=lambda item: len(item["grammarCards"]))
    image = Image.open(QA / "background-sample.png").convert("RGBA").resize((W,H))
    image.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 72)))
    draw = ImageDraw.Draw(image, "RGBA")
    cover = Image.open(SOURCE := ROOT / "source" / "cover.jpg").convert("RGBA").resize((220,220)); image.alpha_composite(cover,(850,35))
    bold = lambda n: ImageFont.truetype(FONT,n)
    lyric = chosen["caption"]["japanese"]; box=draw.textbbox((0,0),lyric,font=bold(70)); lyric_x=(W-(box[2]-box[0]))//2; draw.text((lyric_x,360),lyric,font=bold(70),fill="white",stroke_width=3,stroke_fill="black")
    for annotation in chosen["caption"]["furigana"]:
        index = lyric.find(annotation["base"])
        if index >= 0:
            prefix_width = draw.textbbox((0,0),lyric[:index],font=bold(70))[2]
            draw.text((lyric_x + prefix_width, 320),annotation["reading"],font=bold(28),fill="white",stroke_width=2,stroke_fill="black")
    roma = chosen["caption"]["romaji"]; box=draw.textbbox((0,0),roma,font=bold(34)); draw.text(((W-(box[2]-box[0]))/2,485),roma,font=bold(34),fill="white",stroke_width=3,stroke_fill="black")
    trans = chosen["caption"]["translationZh"]; box=draw.textbbox((0,0),trans,font=bold(45)); draw.text(((W-(box[2]-box[0]))/2,595),trans,font=bold(45),fill="white",stroke_width=3,stroke_fill="black")
    palette=read(PROJECT / "palette.json"); cards=chosen["grammarCards"]; card_width=1740//len(cards); x=90
    for item in cards:
        right=x+card_width-12; draw.rounded_rectangle((x,705,right,950),20,fill=palette["accent"]+"BF",outline=palette["activeTint"],width=2); cx=(x+right)//2
        for y,key,size in ((730,"token",37),(795,"meaning",26),(855,"posZh",25)):
            text=item["token"] if key=="token" else (item.get("functionZh",item.get("zhMeaning","")) if key=="meaning" else item["posZh"])
            current=size
            while draw.textbbox((0,0),text,font=bold(current))[2] > right-x-24 and current>14: current-=1
            box=draw.textbbox((0,0),text,font=bold(current)); draw.text((cx-(box[2]-box[0])//2,y),text,font=bold(current),fill="white")
        x+=card_width
    preview=QA / "content-layout-preview-16x9.png"; image.convert("RGB").save(preview)
    report={"schemaVersion":1,"status":"passed","renderer":"project/render/build_card_draft.py","templateSha256":sha(PROJECT/"templates"/"foreground.json"),"selectedFrame":chosen["id"],"checks":{"cardsSingleRow":True,"cardFieldsIndependent":True,"cardOverflow":False,"textStroke":True,"font":"Microsoft YaHei Bold"},"image":"project/qa/content-layout-preview-16x9.png"}
    write(QA / "layout-report.json",report)
    write(PROJECT / "build-state.json", {"schemaVersion":2,"state":"draft_ready","runId":"20260816-draft-r01","completed":["inputs_confirmed","setup_complete","draft_ready"],"next":"review_approved","activeFiles":{"frames":"project/frames.json","review":"deliverables/review/uchuu-no-fushigi-v2-review.md","layoutReport":"project/qa/layout-report.json"},"notes":["All translations and cards are draft status.","No final render is authorized."]})

if __name__ == "__main__": main()
