"""Build an editable, QRC-safe learning-card draft. No field is human-confirmed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"C:\project\musicjlpt\projects\silhouette-dance\project\work\draft-deps")
from janome.tokenizer import Tokenizer
from pykakasi import kakasi

ROOT = Path(__file__).resolve().parents[2]
PROJECT, SOURCE = ROOT / "project", ROOT / "source"
FONT = "C:/Windows/Fonts/msyhbd.ttc"
W, H = 1920, 1080
TOKENIZER, KAKASI = Tokenizer(), kakasi()

PARTICLES = {
    "は": ("主题提示", "提示助词"), "が": ("主语标记", "格助词"), "を": ("动作对象", "格助词"),
    "に": ("到达点／作用对象", "格助词"), "で": ("动作地点／手段", "格助词"), "と": ("共同对象／引用", "格助词"),
    "の": ("所属／修饰", "格助词"), "も": ("添加、强调或让步", "副助词"), "へ": ("移动方向", "格助词"),
    "から": ("起点／原因", "格助词"), "まで": ("终点／范围", "副助词"), "や": ("列举", "并列助词"),
    "ね": ("征求认同／语气", "终助词"), "よ": ("告知／强调", "终助词"), "か": ("疑问", "终助词")
}
POS = {"名詞": "名词", "動詞": "动词", "形容詞": "形容词", "副詞": "副词", "連体詞": "连体词", "代名詞": "代词", "助詞": "助词", "助動詞": "助动词", "接続詞": "连词", "感動詞": "感叹词", "フィラー": "感叹词"}
LOANWORDS = {"アモーレ": "amore", "ラブ": "love", "チャンス": "chance", "ドキドキ": "doki-doki", "リアル": "real", "ムリ": "impossible", "キス": "kiss", "ハート": "heart", "ダンス": "dance", "パーティー": "party", "ロマン": "roman", "ドラマ": "drama", "スイート": "sweet", "ビター": "bitter"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def hira(value: str) -> str:
    return "".join(chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch for ch in value)


def romaji(value: str) -> str:
    return " ".join(piece["hepburn"] for piece in KAKASI.convert(value))


def has_japanese(value: str) -> bool:
    return any("ぁ" <= ch <= "ゖ" or "ァ" <= ch <= "ヺ" or "一" <= ch <= "龯" for ch in value)


def is_kanji(ch: str) -> bool:
    return "一" <= ch <= "龯"


def kanji_annotations(token: str, reading: str) -> list[dict]:
    """Return only kanji runs; literal kana is used as the alignment anchor."""
    result, remaining = [], reading
    pos = 0
    while pos < len(token):
        if not is_kanji(token[pos]):
            if remaining:
                remaining = remaining[1:]
            pos += 1
            continue
        end = pos
        while end < len(token) and is_kanji(token[end]):
            end += 1
        base = token[pos:end]
        suffix = ""
        probe = end
        while probe < len(token) and not is_kanji(token[probe]):
            suffix += token[probe]
            probe += 1
        if suffix and suffix in remaining:
            run_reading = remaining.split(suffix, 1)[0]
        elif probe == len(token):
            run_reading = remaining
        else:
            run_reading = remaining
        if run_reading:
            result.append({"base": base, "reading": run_reading, "romaji": romaji(run_reading)})
        remaining = remaining[len(run_reading):]
        pos = end
    return result


def card_from(token) -> dict | None:
    surface = token.surface
    if not surface.strip() or not has_japanese(surface):
        return None
    feature = token.part_of_speech.split(",")
    pos1 = feature[0]
    reading = getattr(token, "reading", "*")
    reading = hira(surface if reading in {None, "*"} else reading)
    card = {"token": surface, "reading": reading, "romaji": romaji(surface), "posZh": POS.get(pos1, "待审词性"), "status": "draft", "fieldProvenance": "Janome 0.5.0 + pykakasi 2.3.0 auto draft"}
    if surface in PARTICLES:
        card["functionZh"], card["posZh"] = PARTICLES[surface]
    else:
        card["zhMeaning"] = "待审核含义"
    if surface in LOANWORDS:
        card["sourceWord"] = LOANWORDS[surface]
    return card


def wrap(draw, text, font, width):
    lines, current = [], ""
    for char in text:
        proposal = current + char
        if current and draw.textbbox((0, 0), proposal, font=font)[2] > width:
            lines.append(current); current = char
        else:
            current = proposal
    if current: lines.append(current)
    return lines


def fit_font(draw, text, start, minimum, width):
    for size in range(start, minimum - 1, -1):
        font = ImageFont.truetype(FONT, size)
        if draw.textbbox((0, 0), text, font=font)[2] <= width:
            return font
    return None


def render_preview(frames: list[dict]) -> dict:
    sample = max(frames, key=lambda item: (len(item["grammarCards"]), len(item["caption"]["japanese"])))
    background = Image.open(PROJECT / "qa" / "background-sample.png").convert("RGB").resize((W, H)).convert("RGBA")
    background.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 130)))
    background.alpha_composite(Image.open(SOURCE / "cover.jpg").convert("RGBA").resize((220, 220)), (850, 35))
    draw = ImageDraw.Draw(background)
    jp, zh = ImageFont.truetype(FONT, 64), ImageFont.truetype(FONT, 42)
    text = sample["caption"]["japanese"]
    width = draw.textbbox((0, 0), text, font=jp)[2]
    draw.text(((W - width) / 2, 345), text, font=jp, fill="white", stroke_width=4, stroke_fill="black")
    translation = sample["caption"]["translationZh"]
    width = draw.textbbox((0, 0), translation, font=zh)[2]
    draw.text(((W - width) / 2, 505), translation, font=zh, fill="white", stroke_width=3, stroke_fill="black")
    cards, gap, x, total = sample["grammarCards"], 12, 95, 1730
    card_width = (total - gap * (len(cards) - 1)) // max(1, len(cards))
    failures = []
    for card in cards:
        right = x + card_width
        card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_layer)
        card_draw.rounded_rectangle((x, 600, right, 850), radius=20, fill=(224, 64, 96, 128), outline=(255, 71, 108, 220), width=2)
        background.alpha_composite(card_layer)
        inner = card_width - 28
        token_font = fit_font(draw, card["token"], 37, 18, inner)
        pos_font = fit_font(draw, card["posZh"], 25, 15, inner)
        meaning = card.get("functionZh", card.get("zhMeaning", "待审核含义"))
        meaning_font = fit_font(draw, meaning, 26, 16, inner)
        lines = wrap(draw, meaning, meaning_font, inner) if meaning_font else []
        if not token_font or not pos_font or not meaning_font or len(lines) > 2:
            failures.append(card["token"])
        else:
            for y, value, font in [(625, card["token"], token_font), (770, card["posZh"], pos_font)]:
                box = draw.textbbox((0, 0), value, font=font); draw.text((x + (card_width - (box[2]-box[0]))/2, y), value, font=font, fill="white", stroke_width=2, stroke_fill="black")
            for index, line in enumerate(lines):
                box = draw.textbbox((0, 0), line, font=meaning_font); draw.text((x + (card_width - (box[2]-box[0]))/2, 690 + index * 32), line, font=meaning_font, fill="white", stroke_width=2, stroke_fill="black")
        x = right + gap
    output = PROJECT / "qa" / "content-layout-preview-16x9.png"
    background.convert("RGB").save(output)
    return {"sample": sample["id"], "cardCount": len(cards), "failures": failures, "preview": "project/qa/content-layout-preview-16x9.png"}


def main():
    raw = load(PROJECT / "frames.json")["frames"]
    frames = []
    for shell in raw:
        text = shell["caption"]["japanese"]
        if not has_japanese(text):
            frame = dict(shell); frame["caption"] = dict(shell["caption"], translationStatus="draft-qmts-or-pending"); frame["grammarCards"] = []; frame["status"] = "draft-needs-human-review"; frames.append(frame); continue
        cards = [card for token in TOKENIZER.tokenize(text) if (card := card_from(token))]
        annotations = [item for card in cards for item in kanji_annotations(card["token"], card["reading"])]
        frame = dict(shell)
        frame["caption"] = dict(shell["caption"], furigana=annotations, translationStatus="draft-qmts-source")
        frame["grammarCards"] = cards
        frame["status"] = "draft-needs-human-review"
        frames.append(frame)
    write(PROJECT / "frames.json", {"schemaVersion": 2, "frames": frames})
    particle = {token: {"functionZh": value[0], "posZh": value[1]} for token, value in PARTICLES.items()}
    write(PROJECT / "review" / "particle-functions.json", {"schemaVersion": 1, "functions": particle})
    layout = render_preview(frames)
    report = {"schemaVersion": 1, "result": "passed" if not layout["failures"] else "failed", "preview": layout["preview"], "representative": {"maximumCards": layout["sample"], "maximumCardCount": layout["cardCount"]}, "cardCheck": {"meaningMaxLines": 2, "tokenAndPosOneLine": True, "overflowTokens": layout["failures"]}, "unresolved": ["All automatically generated meanings, POS labels, token boundaries, and QMTS-aligned translations require review.", "Mixed Japanese-English lines preserve QRC display order; English has no cards or annotation."]}
    write(PROJECT / "qa" / "layout-report.json", report)
    review = ["# Amore｜词卡审核稿", "", "所有拆词、词性、含义与非 QMTS 翻译均为自动草稿；请按帧号直接修改或指出需要替换的词卡。助词卡展示功能，不展示字典义。", ""]
    for frame in frames:
        cap = frame["caption"]
        review += [f"## {frame['id']}　{frame['startMs']/1000:06.2f}", f"歌词：{cap['japanese']}", f"暂定中文：{cap['translationZh']}", "", "待核词卡："]
        if not frame["grammarCards"]:
            review.append("- 纯英文行：不显示假名、罗马音或词卡。")
        for card in frame["grammarCards"]:
            meaning = card.get("functionZh", card.get("zhMeaning", "待审核含义"))
            review += [f"- `{card['token']}`｜{card['reading']}｜{card['romaji']}", f"  - 暂定：{meaning}", f"  - 词性：{card['posZh']}"]
        review.append("")
    (ROOT / "deliverables" / "review" / "amore-review.md").write_text("\n".join(review), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
