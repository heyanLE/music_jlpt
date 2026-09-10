"""Render HALO using the approved assisted-review data and the current series rules."""
import json
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
ARCHIVE = ROOT.parent
SOURCE = ARCHIVE / "source"
OUT = ARCHIVE / "deliverables"
DATA_PATH = ROOT / "halo.frames.assisted.review.json"
data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

# Confirmed loanword spellings for the annotation row above each katakana token.
SOURCE_WORDS = {"スペース": "space", "キャンバス": "canvas", "シグナル": "signal"}
for frame in data["frames"]:
    for card in frame["grammarCards"]:
        if card["token"] in SOURCE_WORDS:
            card["sourceWord"] = SOURCE_WORDS[card["token"]]
DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

QRC = json.loads((OUT / "halo-qm.parsed.json").read_text(encoding="utf-8"))
W, H, DELAY = 1920, 1080, 0
FONT = "C:/Windows/Fonts/msyhbd.ttc"
COVER = Image.open(SOURCE / "COVER.jpg").convert("RGBA")
AUDIO = SOURCE / "HALO.flac"
BACKGROUND = next(SOURCE.glob("*.mp4"))
OVERLAYS = ROOT / "halo_overlay_segments"
OVERLAYS.mkdir(exist_ok=True)

# Cover-derived magic palette: red-pink with cyan highlights retained for contrast.
ACTIVE = "#FF7597"
CARD_FILL, CARD_OUTLINE = (124, 21, 58, 142), (255, 170, 196, 150)


def F(size): return ImageFont.truetype(FONT, size)
def norm(text): return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if not c.isspace())
def hira(text): return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)
def is_kanji(char): return "一" <= char <= "龯"


def ruby_parts(base, reading):
    reading, result, pos, i = hira(reading), [], 0, 0
    while i < len(base):
        j, kanji_run = i, is_kanji(base[i])
        while j < len(base) and is_kanji(base[j]) == kanji_run: j += 1
        chunk = base[i:j]
        if not kanji_run:
            expected = hira(chunk)
            if reading[pos:pos + len(expected)] == expected: pos += len(expected)
            result.append((chunk, None)); i = j; continue
        following, k = "", j
        while k < len(base) and not is_kanji(base[k]): following += hira(base[k]); k += 1
        stop = reading.find(following, pos) if following else -1
        ruby = reading[pos:stop] if stop >= pos else reading[pos:]
        pos += len(ruby); result.append((chunk, ruby or None)); i = j
    return result


def wrap(draw, text, font, max_width):
    lines, current = [], ""
    for char in str(text):
        trial = current + char
        if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(current); current = char
            if len(lines) == 2: break
        else: current = trial
    if current and len(lines) < 2: lines.append(current)
    if len("".join(lines)) < len(str(text)):
        tail = lines[-1]
        while tail and draw.textbbox((0, 0), tail + "…", font=font)[2] > max_width: tail = tail[:-1]
        lines[-1] = tail + "…"
    return lines


def centered(draw, y, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


qrc_lines = []
for line in QRC["content"]:
    parts = []
    for part in line["content"]:
        text = norm(part["content"])
        if text: parts.append((line["start"] + part["start"], line["start"] + part["start"] + part["duration"], text))
    joined = "".join(item[2] for item in parts)
    if joined: qrc_lines.append((line["start"], line["start"] + line["duration"], joined, parts))


def qrc_match(frame):
    target, candidates = norm(frame["caption"]["japanese"]), []
    for index, (start, _, _, _) in enumerate(qrc_lines):
        joined, pieces, end = "", [], start
        for _, line_end, line_text, line_parts in qrc_lines[index:index + 4]:
            joined += line_text; pieces += line_parts; end = line_end
            offset = joined.find(target)
            if offset >= 0: candidates.append((abs(start - frame["startMs"]), offset, pieces))
            if end > frame["endMs"] + 1500: break
    return None if not candidates else min(candidates)[1:]


timeline, cursor, unmatched = [(0, DELAY, {"kind": "gap"}, None)], 0, []
for frame in data["frames"]:
    start, end = frame["startMs"], frame["endMs"]
    if cursor < start: timeline.append((cursor + DELAY, start + DELAY, {"kind": "gap"}, None))
    cursor = max(cursor, end)
    match = qrc_match(frame)
    if not match:
        unmatched.append(frame["id"]); timeline.append((start + DELAY, end + DELAY, frame, None)); continue
    offset, pieces = match
    card_ends, n = [], 0
    for card in frame["grammarCards"]:
        n += len(norm(card["token"])); card_ends.append(n)
    local, source_pos = start, 0
    for piece_start, piece_end, text in pieces:
        before, source_pos = source_pos, source_pos + len(text)
        overlap_start, overlap_end = max(before, offset), min(source_pos, offset + n)
        if overlap_start >= overlap_end: continue
        piece_start, piece_end = max(piece_start, start), min(piece_end, end)
        if local < piece_start: timeline.append((local + DELAY, piece_start + DELAY, frame, None))
        position = overlap_start - offset
        active = next((i for i, edge in enumerate(card_ends) if position < edge), None)
        if piece_end > piece_start: timeline.append((piece_start + DELAY, piece_end + DELAY, frame, active))
        local = max(local, piece_end)
    if local < end: timeline.append((local + DELAY, end + DELAY, frame, None))
if cursor < data["project"]["durationMs"]: timeline.append((cursor + DELAY, data["project"]["durationMs"] + DELAY, {"kind": "gap"}, None))


def render(frame, active, path):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw = ImageDraw.Draw(image, "RGBA")
    if frame["kind"] != "lyric": image.save(path); return
    # HALO keeps instrumental footage untouched; only lyric sections receive a veil.
    draw.rectangle((0, 0, W, H), fill=(0, 0, 0, 110))
    cover = COVER.copy(); cover.thumbnail((220, 220)); image.alpha_composite(cover, ((W - cover.width) // 2, 42))
    cards = [item for item in frame["grammarCards"] if item["render"]]
    items = [{"base": c["token"], "reading": c["reading"], "romaji": c["romaji"], "sourceWord": c.get("sourceWord")} for c in cards]
    if not items:
        centered(draw, 390, frame["caption"]["japanese"], F(64), "white")
    else:
        main, note, romaji = F(78), F(30), F(36)
        widths = [draw.textbbox((0, 0), item["base"], font=main)[2] for item in items]
        x, gap = (W - (sum(widths) + 12 * (len(widths) - 1))) / 2, 12
        for index, (item, width) in enumerate(zip(items, widths)):
            color, px = (ACTIVE if index == active else "white"), x
            for base, reading in ruby_parts(item["base"], item["reading"]):
                draw.text((px, 360), base, font=main, fill=color)
                if reading: draw.text((px, 320), reading, font=note, fill=color)
                px += draw.textbbox((0, 0), base, font=main)[2]
            if item["sourceWord"]:
                draw.text((x, 320), item["sourceWord"], font=note, fill=color)
            box = draw.textbbox((0, 0), item["romaji"], font=romaji)
            draw.text((x + (width - (box[2] - box[0])) / 2, 495), item["romaji"], font=romaji, fill=color)
            x += width + gap
    centered(draw, 605, frame["caption"]["translationZh"], F(48), (245, 245, 245, 238))
    if cards:
        total, gap, x = 1740, 12, 90
        widths = [total // len(cards)] * len(cards); widths[-1] += total - sum(widths)
        for item, width in zip(cards, widths):
            draw.rounded_rectangle((x, 705, x + width - gap, 950), 20, fill=CARD_FILL, outline=CARD_OUTLINE, width=2)
            cx = x + (width - gap) / 2
            box = draw.textbbox((0, 0), item["token"], font=F(36)); draw.text((cx - (box[2] - box[0]) / 2, 730), item["token"], font=F(36), fill="white")
            for index, text in enumerate(wrap(draw, item.get("functionZh", item["zhMeaning"]), F(27), width - gap - 24)):
                box = draw.textbbox((0, 0), text, font=F(27)); draw.text((cx - (box[2] - box[0]) / 2, 790 + index * 31), text, font=F(27), fill="white")
            box = draw.textbbox((0, 0), item["posZh"], font=F(26)); draw.text((cx - (box[2] - box[0]) / 2, 875), item["posZh"], font=F(26), fill="white")
            x += width
    image.save(path)


concat = []
for index, (start, end, frame, active) in enumerate(timeline):
    if end <= start: continue
    path = OVERLAYS / f"{index:04d}.png"; render(frame, active, path)
    concat += [f"file '{path.as_posix()}'", f"duration {(end - start) / 1000:.3f}"]
concat += [f"file '{(OVERLAYS / f'{len(timeline) - 1:04d}.png').as_posix()}'"]
concat_path = ROOT / "halo_overlay.concat.txt"; concat_path.write_text("\n".join(concat), encoding="utf-8")
target = OUT / "halo-qrc-composite-v1.mp4"
# Fit the 4:3 MV to the 16:9 learning canvas by height, then pillarbox it.
# This preserves every source pixel and keeps the lyric overlay at 1920×1080.
filter_graph = "[0:v]scale=-2:1080,pad=1920:1080:(ow-iw)/2:0:black[bg];[1:v]format=rgba[ov];[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(BACKGROUND), "-f", "concat", "-safe", "0", "-i", str(concat_path), "-i", str(AUDIO), "-filter_complex", filter_graph, "-map", "[v]", "-map", "2:a", "-r", "24000/1001", "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "320k", "-shortest", str(target)], check=True)
print("unmatched QRC frames:", unmatched)
print(target)
