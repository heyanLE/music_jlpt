import html
import json
import re
import statistics
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DELIVERABLES = ROOT / "deliverables"
PROJECT = ROOT / "project"
SLUG = "mou-dou-natte-mo-ii-ya"


def extract_qrc_text(path):
    raw_xml = path.read_text(encoding="utf-8")
    match = re.search(r'<Lyric_1\s+[^>]*LyricContent="(.*?)"\s*/>', raw_xml, re.DOTALL)
    if not match:
        raise ValueError(f"Lyric_1 content not found in {path}")
    return html.unescape(match.group(1)).replace("\r\n", "\n")


def parse_qrc(path):
    lines = []
    for raw in extract_qrc_text(path).splitlines():
        match = re.match(r"^\[(\d+),(\d+)\](.*)$", raw)
        if not match:
            continue
        start, duration, body = match.groups()
        parts = []
        for text, word_start, word_duration in re.findall(r"(.*?)\((\d+),(\d+)\)", body):
            if text:
                parts.append({"text": text, "startMs": int(word_start), "durationMs": int(word_duration)})
        if parts:
            lines.append({"startMs": int(start), "durationMs": int(duration), "text": "".join(x["text"] for x in parts), "parts": parts})
    return lines


def parse_lrc(path):
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$", raw)
        if match and match.group(3).strip() and match.group(3).strip() != "//":
            minutes, seconds, text = match.groups()
            rows.append({"startMs": int((int(minutes) * 60 + float(seconds)) * 1000), "text": text.strip()})
    return rows


def translation_for(start_ms, translations):
    candidates = [r for r in translations if abs(r["startMs"] - start_ms) <= 1800]
    if not candidates:
        return ""
    return min(candidates, key=lambda r: abs(r["startMs"] - start_ms))["text"]


def palette_from_cover(path):
    image = Image.open(path).convert("RGB").resize((128, 128))
    candidates = []
    for red, green, blue in image.getdata():
        top, bottom = max(red, green, blue), min(red, green, blue)
        saturation = 0 if top == 0 else (top - bottom) / top
        if saturation >= 0.42 and 35 < top < 240:
            candidates.append((red, green, blue))
    if not candidates:
        candidates = list(image.getdata())
    red, green, blue = (round(statistics.mean(x[i] for x in candidates)) for i in range(3))
    return {
        "accent": "#%02X%02X%02X" % (red, green, blue),
        "activeTint": "#%02X%02X%02X" % tuple(min(255, round(c + (255 - c) * .45)) for c in (red, green, blue)),
        "cardFill": "#11151DEB",
        "body": "#FFFFFF",
        "muted": "#DCE3F0",
    }


def make_cover(width, height, palette, suffix):
    accent = tuple(int(palette["accent"][i:i + 2], 16) for i in (1, 3, 5))
    background = Image.new("RGB", (width, height), (10, 14, 24))
    art = Image.open(DELIVERABLES / f"{SLUG}-cover.jpg").convert("RGB")
    art.thumbnail((height * .54, height * .54))
    blur = art.resize((width, height)).filter(ImageFilter.GaussianBlur(28))
    background = Image.blend(background, blur, .18)
    draw = ImageDraw.Draw(background)
    draw.rounded_rectangle((0, 0, width, height), radius=0, fill=(7, 11, 20))
    draw.rectangle((0, 0, int(width * .018), height), fill=accent)
    art = Image.open(DELIVERABLES / f"{SLUG}-cover.jpg").convert("RGB")
    art.thumbnail((int(height * .48), int(height * .48)))
    x, y = int(width * .11), int(height * .27)
    background.paste(art, (x, y))
    font_path = r"C:\Windows\Fonts\msyh.ttc"
    title_font = ImageFont.truetype(font_path, int(height * .062))
    body_font = ImageFont.truetype(font_path, int(height * .040))
    draw = ImageDraw.Draw(background)
    tx = x + art.width + int(width * .055)
    draw.text((tx, int(height * .34)), "歌词同步高亮 · 假名", font=title_font, fill=(255, 255, 255))
    draw.text((tx, int(height * .46)), "罗马音 · 语法", font=title_font, fill=(255, 255, 255))
    draw.text((tx, int(height * .60)), "もうどうなってもいいや", font=body_font, fill=(220, 227, 240))
    background.save(DELIVERABLES / f"{SLUG}-cover-{suffix}.png")


original = parse_qrc(DELIVERABLES / f"{SLUG}-qm-decoded.qrc")
romanized = parse_qrc(DELIVERABLES / f"{SLUG}-qmRoma-decoded.qrc")
translations = parse_lrc(DELIVERABLES / f"{SLUG}-qmts-decoded.qrc")
frames = []
for index, line in enumerate(original):
    roma = romanized[index] if index < len(romanized) else {"text": "", "parts": []}
    frames.append({
        "id": f"line-{index + 1:03}",
        "startMs": line["startMs"],
        "durationMs": line["durationMs"],
        "japanese": line["text"],
        "parts": line["parts"],
        "romanizationSource": roma["text"],
        "romanizationParts": roma["parts"],
        "translationZh": translation_for(line["startMs"], translations),
        "review": {"translation": "provisional", "tokens": "pending", "cards": []},
    })

(PROJECT / "frames.review.json").write_text(json.dumps({"frames": frames}, ensure_ascii=False, indent=2), encoding="utf-8")
palette = palette_from_cover(DELIVERABLES / f"{SLUG}-cover.jpg")
(PROJECT / "palette.json").write_text(json.dumps(palette, ensure_ascii=False, indent=2), encoding="utf-8")
make_cover(1920, 1080, palette, "16x9")
make_cover(1440, 1080, palette, "4x3")
review_lines = [f"# {SLUG} review", "", "Review the provisional Chinese translations, tokenization, readings, and cards before rendering.", ""]
for frame in frames:
    review_lines.extend([f"## {frame['id']} · {frame['startMs'] / 1000:.2f}s", "", frame["japanese"], "", f"中文：{frame['translationZh'] or '待补充'}", "", "词卡：待审核", ""])
(DELIVERABLES / f"{SLUG}-review.md").write_text("\n".join(review_lines), encoding="utf-8")
state = {
    "source": ["source/background.mp4", "source/music.flac", "source/lyrics.qm.qrc", "source/lyrics.qmRoma.qrc", "source/lyrics.qmts.qrc"],
    "generated": [f"deliverables/{SLUG}-cover.jpg", f"deliverables/{SLUG}-cover-16x9.png", f"deliverables/{SLUG}-cover-4x3.png", f"deliverables/{SLUG}-qm-decoded.qrc", f"deliverables/{SLUG}-qmRoma-decoded.qrc", f"deliverables/{SLUG}-qmts-decoded.qrc", "project/frames.review.json", "project/palette.json", f"deliverables/{SLUG}-review.md"],
    "counts": {"originalLines": len(original), "romanizedLines": len(romanized), "translations": len(translations)},
}
(PROJECT / "build-state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(state["counts"]))
