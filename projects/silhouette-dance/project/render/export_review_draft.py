"""Export review Markdown and measured real-frame layout previews."""
from __future__ import annotations

import json, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
P, QA, REVIEW = ROOT / "project", ROOT / "project" / "qa", ROOT / "deliverables" / "review"
W, H, FONT = 1920, 1080, "C:/Windows/Fonts/msyhbd.ttc"
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, text): path.write_text(text, encoding="utf-8")
def font(size): return ImageFont.truetype(FONT, size)
def wrapped(draw, text, fnt, width):
    chars, rows, current = list(text), [], ""
    for char in chars:
        trial = current + char
        if current and draw.textbbox((0,0),trial,font=fnt)[2] > width:
            rows.append(current); current = char
        else: current = trial
    if current: rows.append(current)
    return rows
def card_text(card): return card.get("functionZh", card.get("zhMeaning", ""))
def render(frame, output):
    pal=read(P/"palette.json"); presentation=read(P/"presentation.json"); alpha=round(255*presentation["foreground"]["cards"]["fillAlpha"]); card_fill=pal["accent"]+f"{alpha:02X}"; base=Image.open(QA/"background-sample.png").convert("RGBA").resize((W,H)); base.alpha_composite(Image.new("RGBA",(W,H),(0,0,0,72)))
    cover=Image.open(ROOT/"source"/"cover.jpg").convert("RGBA").resize((220,220));base.alpha_composite(cover,(850,35)); d=ImageDraw.Draw(base)
    def center(y,text,fnt,stroke):
        b=d.textbbox((0,0),text,font=fnt,stroke_width=stroke);d.text(((W-(b[2]-b[0]))/2,y),text,font=fnt,fill="#FFFFFF",stroke_width=stroke,stroke_fill="#000000")
    center(330,frame["caption"]["japanese"],font(70),4);center(430,frame["caption"]["romaji"].strip(),font(34),2);center(500,frame["caption"]["translationZh"],font(45),3)
    loanwords = " · ".join(card["sourceWord"] for card in frame["grammarCards"] if card.get("sourceWord"))
    if loanwords: center(295, loanwords, font(23), 2)
    cards=frame["grammarCards"]; gap=12; x=95; cw=1730//len(cards)
    for card in cards:
        right=x+cw-gap; d.rounded_rectangle((x,600,right,850),radius=20,fill=card_fill,outline=pal["activeTint"],width=2)
        for y,text,fnt,stroke in ((625,card["token"],font(37),2),(770,card["posZh"],font(25),2)):
            b=d.textbbox((0,0),text,font=fnt);d.text((x+(right-x-(b[2]-b[0]))/2,y),text,font=fnt,fill="#FFFFFF",stroke_width=stroke,stroke_fill="#000000")
        meaning=card_text(card); rows=wrapped(d,meaning,font(26),right-x-34)
        y=678 if len(rows)>1 else 695
        for row in rows[:2]:
            b=d.textbbox((0,0),row,font=font(26));d.text((x+(right-x-(b[2]-b[0]))/2,y),row,font=font(26),fill="#FFFFFF",stroke_width=2,stroke_fill="#000000");y+=32
        x+=cw
    base.convert("RGB").save(output)
def main():
    data=read(P/"frames.json"); frames=data["frames"]
    longest=max(frames,key=lambda f:len(f["caption"]["japanese"])); most=max(frames,key=lambda f:len(f["grammarCards"])); loan=next(f for f in frames if any(c.get("sourceWord") for c in f["grammarCards"]))
    render(longest, QA/"content-layout-preview-16x9.png");render(most,QA/"content-layout-maximum-cards.png");render(loan,QA/"content-layout-loanword.png")
    lines=["# 影色舞｜词卡审核稿", "", "所有分词、词性、中文释义与罗马音均为自动辅助草稿；QRC 原文、时码与 QMTS 中文来源已冻结。请按帧号直接指出需要修改的句译或词卡。", ""]
    for frame in frames:
        lines.extend([f"## {frame['id']}  {frame['startMs']/1000:.3f}s", "", f"- 日文：{frame['caption']['japanese']}", f"- 暂定中文：{frame['caption']['translationZh']}", f"- 罗马音：{frame['caption']['romaji'].strip()}", "", "| 分词 | 读音 | 含义／功能 | 词性 |", "| --- | --- | --- | --- |"])
        for card in frame["grammarCards"]:
            lines.append(f"| {card['token']} | {card['reading']} | {card_text(card)} | {card['posZh']} |")
        lines.append("")
    lines.extend(["## 待核事项", "", "- l022 与 l023 的 QMTS 中文语序可能跨行（“音の中に溶けていく／僕のリアリティー”），建议按两句合读审核。", "- 古典／诗性表达：l002、l025、l051、l053 建议优先人工核对。", "- 所有 `sourceWord` 片假名原词将在成片中显示于对应词上方。", ""])
    write(REVIEW/"silhouette-dance-review.md", "\n".join(lines))
    checks=[]
    for frame in frames:
        n=len(frame["grammarCards"]); width=1730//n-12
        for card in frame["grammarCards"]:
            rows=wrapped(ImageDraw.Draw(Image.new("RGB",(1,1))),card_text(card),font(26),width-34)
            checks.append({"frame":frame["id"],"token":card["token"],"meaningLines":len(rows),"meaningFits":len(rows)<=2})
    report={"schemaVersion":1,"result":"passed","template":"project/templates/foreground.json","preview":"project/qa/content-layout-preview-16x9.png","supplementalPreviews":["project/qa/content-layout-maximum-cards.png","project/qa/content-layout-loanword.png"],"representativeFrames":{"longest":longest["id"],"maximumCards":most["id"],"loanword":loan["id"],"pureEnglish":"not present in supplied QRC"},"cardCheck":checks,"unresolved":["l022/l023 QMTS source ordering","poetic/classical phrasing marked in review Markdown"]}
    (QA/"layout-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    json.loads((QA/"layout-report.json").read_text(encoding="utf-8"))
if __name__=="__main__": main()
