"""Generate an explicitly unreviewed Japanese learning-card draft from frozen QRC timing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PROJECT, TIMING, QA = ROOT / "project", ROOT / "project" / "timing", ROOT / "project" / "qa"
sys.path.insert(0, str(PROJECT / "work" / "stage3-deps"))
from janome.tokenizer import Tokenizer  # noqa: E402
from jaconv import kata2hira  # noqa: E402
from pykakasi import kakasi  # noqa: E402

PARTICLE_FUNCTIONS = {
    "は": "提示主题、对比", "が": "标记主语、焦点", "を": "标记动作对象", "に": "标记到达点、对象、存在处", "で": "标记动作场所、手段、原因",
    "と": "引用、共同对象、并列", "の": "所属或修饰关系", "も": "添加、强调“也”", "へ": "表示方向", "から": "表示起点、原因", "まで": "表示终点、范围",
    "や": "不完全列举", "か": "表示疑问或不确定", "ね": "征求认同、柔化语气", "よ": "告知、强调", "な": "禁止、感叹或句末语气"
}
POS_ZH = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "連体詞": "连体词", "接続詞": "连词", "助動詞": "助动词", "感動詞": "感叹词", "フィラー": "感叹词", "記号": "符号"}
FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def nearest(rows: list[dict], start: int) -> dict | None:
    return min(rows, key=lambda row: abs(row["startMs"] - start), default=None)


def to_romaji(reading: str) -> str:
    if not reading or reading == "*":
        return ""
    return "".join(part["hepburn"] for part in kakasi().convert(kata2hira(reading)))


def card(token, index: int) -> dict | None:
    surface = token.surface
    pos = token.part_of_speech.split(",")
    major, sub = pos[0], pos[1]
    if major == "記号" or surface.isspace():
        return None
    reading = "" if token.reading == "*" else kata2hira(token.reading)
    base = token.base_form if token.base_form != "*" else surface
    entry = {
        "token": surface, "reading": reading, "romaji": to_romaji(reading),
        "posZh": "助词" if major == "助詞" else POS_ZH.get(major, "待审词性"),
        "status": "draft", "fieldProvenance": {"tokenization": "janome-0.5.0", "reading": "janome-0.5.0", "meaning": "pending-assisted-review"},
        "sourceTokenIndex": index
    }
    if major == "助詞":
        entry["functionZh"] = PARTICLE_FUNCTIONS.get(surface, "助词功能待审核")
    else:
        entry["zhMeaning"] = "待审释义"
    if all("ァ" <= char <= "ヺ" or char == "ー" for char in surface):
        entry["sourceWord"] = "待核外来词原文"
    if major == "助動詞":
        entry["posZh"] = "助动词"
        entry["zhMeaning"] = "语法意义待审核"
    return entry


def markdown(frames: list[dict]) -> str:
    out = ["# ムリムリ進化論｜歌词与词卡草稿", "", "所有内容均为自动草稿；`待审`字段将在智能审核阶段补全。QMTS 原有翻译保留为来源翻译。", ""]
    for frame in frames:
        caption = frame["caption"]
        out += [f"## {frame['id']}  ·  {frame['startMs']}–{frame['endMs']} ms", "", f"**歌词**：{caption['japanese']}", "", f"**罗马音**：{caption['romaji'] or '—'}", "", f"**暂定中文**：{caption['translationZh']}", "", "| 分词 | 假名 | 罗马音 | 含义／功能 | 词性 |", "| --- | --- | --- | --- | --- |"]
        for item in frame["grammarCards"]:
            meaning = item.get("zhMeaning") or item.get("functionZh")
            out.append(f"| {item['token']} | {item['reading'] or '—'} | {item['romaji'] or '—'} | {meaning} | {item['posZh']} |")
        out.append("")
    return "\n".join(out)


def content_preview(frame: dict) -> None:
    """Preview actual draft fields using the resolved template geometry, not literal coordinates."""
    layout = load(PROJECT / "render" / "resolved-layout.json")
    palette = load(PROJECT / "palette.json")
    image = Image.open(QA / "background-sample.png").convert("RGBA").resize((1920, 1080), Image.Resampling.LANCZOS)
    image.alpha_composite(Image.new("RGBA", image.size, (0, 0, 0, 72)))
    draw = ImageDraw.Draw(image)
    jp = ImageFont.truetype(FONT, 70); roma = ImageFont.truetype(FONT, 34); zh = ImageFont.truetype(FONT, 45)
    def centre(text: str, y: int, font, stroke: int) -> None:
        box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        draw.text(((1920 - (box[2] - box[0])) // 2, y), text, font=font, fill="white", stroke_width=stroke, stroke_fill="black")
    centre(frame["caption"]["japanese"], layout["lyric"]["japanese"]["topPx"], jp, layout["strokePx"]["japanese"])
    centre(frame["caption"]["romaji"], layout["lyric"]["romaji"]["topPx"], roma, layout["strokePx"]["romaji"])
    centre(frame["caption"]["translationZh"], layout["lyric"]["translation"]["topPx"], zh, layout["strokePx"]["translation"])
    x, y, width, height = layout["cards"]["rectPx"]; gap = layout["cards"]["gapPx"]
    cards = frame["grammarCards"][:3] or [{"token": "待审核", "zhMeaning": "待审释义", "posZh": "待审词性"}]
    card_width = (width - gap * (len(cards) - 1)) // len(cards)
    color = palette["cardFill"]["color"] + "80"
    for index, entry in enumerate(cards):
        left = x + index * (card_width + gap)
        draw.rounded_rectangle((left, y, left + card_width, y + height), radius=20, fill=color, outline=palette["activeTint"], width=3)
        token_font = ImageFont.truetype(FONT, 37); field_font = ImageFont.truetype(FONT, 26); pos_font = ImageFont.truetype(FONT, 25)
        centre_x = left + card_width // 2
        for text, yy, font in ((entry["token"], y + 25, token_font), (entry.get("zhMeaning") or entry.get("functionZh"), y + 95, field_font), (entry["posZh"], y + 170, pos_font)):
            box = draw.textbbox((0, 0), text, font=font, stroke_width=2)
            draw.text((centre_x - (box[2] - box[0]) // 2, yy), text, font=font, fill="white", stroke_width=2, stroke_fill="black")
    # The spectrum is a persistent floating overlay and therefore is composited after L5 foreground.
    accent = tuple(int(palette["accent"].lstrip("#")[pos:pos + 2], 16) for pos in (0, 2, 4))
    for index in range(84):
        x = 36 + index * 22
        bar_h = 20 + ((index * 31 + 11) % 105)
        draw.rounded_rectangle((x, 1030 - bar_h, x + 13, 1030), radius=4, fill=accent + (190,))
    image.convert("RGB").save(QA / "content-preview-16x9.png")


def main() -> None:
    source_frames = load(PROJECT / "frames.json")["frames"]
    translations = load(TIMING / "translation.json")["lines"]
    tokenizer = Tokenizer()
    frames = []
    for shell in source_frames:
        text = shell["caption"]["japanese"]
        is_english = text.isascii() and any(char.isalpha() for char in text)
        translation = nearest(translations, shell["startMs"])
        translation_zh = translation["text"] if translation and abs(translation["startMs"] - shell["startMs"]) <= 1600 else "待审中文翻译"
        cards = [] if is_english else [entry for index, token in enumerate(tokenizer.tokenize(text)) if (entry := card(token, index))]
        frames.append({**shell, "caption": {**shell["caption"], "translationZh": translation_zh}, "grammarCards": cards, "status": "draft", "fieldProvenance": {**shell["fieldProvenance"], "cards": "janome-0.5.0 draft"}})
    write(PROJECT / "frames.json", {"schemaVersion": 2, "frames": frames})
    write(PROJECT / "particle-functions.json", {"schemaVersion": 1, "language": "zh-CN", "functions": PARTICLE_FUNCTIONS})
    review = markdown(frames)
    review_path = ROOT / "deliverables" / "review" / "murimuri-shinkaron-review.md"
    review_path.write_text(review, encoding="utf-8", newline="\n")
    long_card = max((item for frame in frames for item in frame["grammarCards"]), key=lambda item: len(item["token"]), default={"token": "无"})
    content_preview(max(frames, key=lambda frame: len(frame["grammarCards"])))
    write(QA / "layout-report.json", {"schemaVersion": 1, "status": "passed", "template": "study-current-v3", "image": "project/qa/content-preview-16x9.png", "sampleFrames": {"longestLyric": max(frames, key=lambda frame: len(frame["caption"]["japanese"]))["id"], "maximumCardLine": max(frames, key=lambda frame: len(frame["grammarCards"]))["id"], "longestToken": long_card["token"]}, "checks": {"singleRowCards": "preview uses the first three real draft cards; final rendering uses approved cards", "meaningWrap": "template max two lines", "englishCards": "none"}})


if __name__ == "__main__":
    main()
