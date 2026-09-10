"""Build a reviewable lyric/card draft from decoded QQ Music artifacts."""
import json
import re
from pathlib import Path
from fugashi import Tagger
from pykakasi import kakasi

ROOT = Path(__file__).parent
PROJECT, OUT = ROOT.parent, ROOT.parent / "deliverables"
QM = json.loads((OUT / "brand-new-days-qm.parsed.json").read_text(encoding="utf-8"))
ROMA = json.loads((OUT / "brand-new-days-qmRoma.parsed.json").read_text(encoding="utf-8"))
QMTS = (OUT / "brand-new-days-qmts.xml").read_text(encoding="utf-8")
tagger, kks = Tagger(), kakasi()

PARTICLES = {
    "を": ("动作对象", "助词"), "に": ("动作发生的时间／地点", "助词"), "の": ("所属修饰", "助词"),
    "が": ("主语标记", "助词"), "は": ("主题提示", "助词"), "と": ("共同对象／引用", "助词"),
    "で": ("动作的地点／手段", "助词"), "も": ("追加、也", "助词"), "へ": ("移动方向", "助词"),
}
POS = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "連体詞": "连体词", "代名詞": "代词", "助詞": "助词", "助動詞": "助动词", "接続詞": "连词", "感動詞": "感叹词"}

def japanese(text): return any("ぁ" <= c <= "ゖ" or "ァ" <= c <= "ヺ" or "一" <= c <= "龯" for c in text)
def hira(text):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)
def roma(text): return " ".join(x["hepburn"] for x in kks.convert(text))
def qrc_text(line): return "".join(p.get("content", "") for p in line.get("content", []))
def timestamp_ms(value):
    m = re.match(r"\[(\d+):(\d+\.\d+)\](.*)", value)
    return int((int(m.group(1))*60 + float(m.group(2))) * 1000), m.group(3) if m else (0, "")

translations=[]
for row in QMTS.splitlines():
    m=re.match(r"\[(\d+):(\d+\.\d+)\](.*)",row)
    if m and m.group(3).strip() not in {"//", ""}:
        translations.append((int((int(m.group(1))*60+float(m.group(2)))*1000),m.group(3).strip()))
roma_lines=[(x["start"],qrc_text(x)) for x in ROMA.get("content",[]) if qrc_text(x).strip()]

frames=[]
for source in QM["content"]:
    text=qrc_text(source).strip()
    if source["start"] < 10000 or not japanese(text): continue
    translation=next((v for t,v in translations if abs(t-source["start"]) < 1100), "待审中文翻译")
    romaji=next((v for t,v in roma_lines if abs(t-source["start"]) < 250), "")
    cards=[]; furigana=[]
    for word in tagger(text):
        token=word.surface
        if not japanese(token): continue
        pos=getattr(word.feature,"pos1","")
        reading=getattr(word.feature,"pron","") or getattr(word.feature,"kana","") or token
        reading=hira(reading)
        # Existing kana and pure-kana terms deliberately have no ruby rendering.
        card={"token":token,"reading":reading,"romaji":roma(token),"zhMeaning":"待审","posZh":POS.get(pos,"待审"),"render":True}
        if token in PARTICLES:
            card.pop("zhMeaning"); card["functionZh"],card["posZh"]=PARTICLES[token]
        cards.append(card)
        if any("一"<=c<="龯" for c in token): furigana.append({"base":token,"reading":reading,"romaji":card["romaji"]})
    frames.append({"id":f"l{len(frames)+1:03d}","startMs":source["start"],"endMs":source["start"]+source["duration"],"caption":{"japanese":text,"furigana":furigana,"romaji":romaji,"translationZh":translation},"grammarCards":cards,"analysisStatus":"draft-needs-review"})

project={"schemaVersion":"1.0","project":{"id":"brand-new-days-reload","title":"Brand New Days -Reload-","artist":"高橋あず美 & アトラスサウンドチーム","durationMs":352600,"canvas":{"width":1920,"height":1080},"background":"cover-wave"},"reviewStatus":"auto-draft-needs-human-review","frames":frames}
(ROOT/"frames.review.json").write_text(json.dumps(project,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

lines=["# Brand New Days -Reload-｜词卡审核", "", "说明：QQ Music 时间、罗马音和中文为初稿；词卡中文含义与词性待审核。英文仅显示歌词，不生成词卡。", ""]
for frame in frames:
    lines += [f"## {frame['id']}　{frame['startMs']/1000:06.2f}", f"日文：{frame['caption']['japanese']}", f"暂定中文：{frame['caption']['translationZh']}", "", "待核词卡："]
    for card in frame["grammarCards"]:
        meaning=card.get("functionZh",card.get("zhMeaning","待审"))
        lines += [f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}", f"  - 暂定：{meaning}", f"  - 词性：{card['posZh']}"]
    lines.append("")
(OUT/"brand-new-days-review.md").write_text("\n".join(lines),encoding="utf-8")
(ROOT/"build-state.json").write_text(json.dumps({"frameCount":len(frames),"background":"cover-wave","next":"human-review-or-assisted-review"},ensure_ascii=False,indent=2),encoding="utf-8")
print(f"frames: {len(frames)}")
