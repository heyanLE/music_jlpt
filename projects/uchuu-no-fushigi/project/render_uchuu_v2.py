"""Render the skill-compliant V2 of うちゅうのふしぎ."""
import json
import subprocess
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
ARCHIVE = ROOT.parent
SOURCE = ARCHIVE / "source"
DELIVERABLES = ARCHIVE / "deliverables"
DATA = json.loads((ROOT / "uchuu.frames.approved.json").read_text(encoding="utf-8"))
QRC = json.loads((DELIVERABLES / "uchuu-qm.parsed.json").read_text(encoding="utf-8"))
W, H, DELAY = 1920, 1080, 1000
FONT = "C:/Windows/Fonts/msyhbd.ttc"
COVER = Image.open(ROOT / "uchuu-cover.jpg").convert("RGBA")
AUDIO = next(SOURCE.glob("*.flac"))
BACKGROUND = next(SOURCE.glob("*.mp4"))
OVERLAYS = ROOT / "uchuu_v2_overlay_segments"
OVERLAYS.mkdir(exist_ok=True)

# Cover-derived magic colour: luminous lavender/pink from the supplied art.
ACTIVE = "#F0CCFF"
CARD_FILL = (78, 27, 103, 142)
CARD_OUTLINE = (239, 195, 255, 150)


def F(size):
    return ImageFont.truetype(FONT, size)


def clean_display(value):
    return str(value).lstrip("：: ")


def norm(value):
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if not c.isspace())


def hira(value):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in value)


def is_kanji(value):
    return "一" <= value <= "龯"


def ruby_parts(base, reading):
    """Return base/ruby chunks, with ruby only on kanji spans (left-aligned)."""
    reading, result, pos, i = hira(reading), [], 0, 0
    while i < len(base):
        j = i
        kanji_run = is_kanji(base[i])
        while j < len(base) and is_kanji(base[j]) == kanji_run:
            j += 1
        chunk = base[i:j]
        if not kanji_run:
            expected = hira(chunk)
            if reading[pos:pos + len(expected)] == expected:
                pos += len(expected)
            result.append((chunk, None))
            i = j
            continue
        following_kana, k = "", j
        while k < len(base) and not is_kanji(base[k]):
            following_kana += hira(base[k])
            k += 1
        stop = reading.find(following_kana, pos) if following_kana else -1
        ruby = reading[pos:stop] if stop >= pos else reading[pos:]
        pos += len(ruby)
        result.append((chunk, ruby or None))
        i = j
    return result


def centered(draw, y, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


def wrap_card_text(draw, text, font, max_width, max_lines=2):
    """Word-wrap CJK card content within its actual rendered card width."""
    lines, current = [], ""
    for char in str(text):
        trial = current + char
        if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(current)
            current = char
            if len(lines) == max_lines:
                break
        else:
            current = trial
    if current and len(lines) < max_lines:
        lines.append(current)
    # An ellipsis signals a deliberately clipped third line; text never spills out.
    consumed = "".join(lines)
    if len(consumed) < len(str(text)):
        tail = lines[-1]
        while tail and draw.textbbox((0, 0), tail + "…", font=font)[2] > max_width:
            tail = tail[:-1]
        lines[-1] = tail + "…"
    return lines


qrc_lines = []
for line in QRC["content"]:
    parts = []
    for part in line["content"]:
        clean = norm(part["content"])
        if clean:
            parts.append((line["start"] + part["start"], line["start"] + part["start"] + part["duration"], clean))
    joined = "".join(item[2] for item in parts)
    if joined:
        qrc_lines.append((line["start"], line["start"] + line["duration"], joined, parts))


def qrc_match(frame):
    target = norm("".join(card["token"] for card in frame["grammarCards"]))
    candidates = []
    for index, (start, _, _, _) in enumerate(qrc_lines):
        joined, parts, end = "", [], start
        for _, line_end, line_text, line_parts in qrc_lines[index:index + 4]:
            joined += line_text
            parts += line_parts
            end = line_end
            offset = joined.find(target)
            if offset >= 0:
                candidates.append((abs(start - frame["startMs"]), offset, parts))
            if end > frame["endMs"] + 1500:
                break
    if not candidates:
        return None
    _, offset, parts = min(candidates)
    return target, offset, parts


frames, timeline_cursor, unmatched = [(0, DELAY, {"kind": "gap"}, None)], 0, []
for frame in DATA["frames"]:
    start, end = frame["startMs"], frame["endMs"]
    if timeline_cursor < start:
        frames.append((timeline_cursor + DELAY, start + DELAY, {"kind": "gap"}, None))
    timeline_cursor = max(timeline_cursor, end)
    if frame["kind"] != "lyric":
        frames.append((start + DELAY, end + DELAY, frame, None))
        continue
    matched = qrc_match(frame)
    if not matched:
        unmatched.append(frame["id"])
        frames.append((start + DELAY, end + DELAY, frame, None))
        continue
    target, offset, parts = matched
    card_ends, length = [], 0
    for item in frame["grammarCards"]:
        length += len(norm(item["token"]))
        card_ends.append(length)
    cursor, source_pos = start, 0
    for part_start_ms, part_end_ms, text in parts:
        source_start, source_pos = source_pos, source_pos + len(text)
        overlap_start = max(source_start, offset)
        overlap_end = min(source_pos, offset + len(target))
        if overlap_start >= overlap_end:
            continue
        part_start_ms, part_end_ms = max(part_start_ms, start), min(part_end_ms, end)
        if cursor < part_start_ms:
            frames.append((cursor + DELAY, part_start_ms + DELAY, frame, None))
        active_pos = overlap_start - offset
        active = next((i for i, boundary in enumerate(card_ends) if active_pos < boundary), None)
        if part_end_ms > part_start_ms:
            frames.append((part_start_ms + DELAY, part_end_ms + DELAY, frame, active))
        cursor = max(cursor, part_end_ms)
    if cursor < end:
        frames.append((cursor + DELAY, end + DELAY, frame, None))
if timeline_cursor < DATA["project"]["durationMs"]:
    frames.append((timeline_cursor + DELAY, DATA["project"]["durationMs"] + DELAY, {"kind": "gap"}, None))


def display_items(frame):
    items = list(frame["caption"]["furigana"])
    shown = norm(frame["caption"]["japanese"])
    card_text = norm("".join(item["base"] for item in items))
    # Preserve visible Japanese punctuation without turning it into a learning card.
    if shown.endswith("？") and not card_text.endswith("？"):
        items.append({"base": "？", "reading": "", "romaji": ""})
    return items


def render(frame, active, path):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    if frame["kind"] != "lyric":
        image.save(path)
        return
    draw.rectangle((0, 0, W, H), fill=(0, 0, 0, 58))
    cover = COVER.copy()
    cover.thumbnail((220, 220))
    image.alpha_composite(cover, ((W - cover.width) // 2, 42))
    items = display_items(frame)
    main, ruby, romaji = F(78), F(30), F(36)
    widths = [draw.textbbox((0, 0), item["base"], font=main)[2] for item in items]
    gap = 12
    x = (W - (sum(widths) + gap * (len(widths) - 1))) / 2
    for index, (item, width) in enumerate(zip(items, widths)):
        color = ACTIVE if index == active else "white"
        part_x = x
        for base, reading in ruby_parts(item["base"], item["reading"]):
            draw.text((part_x, 360), base, font=main, fill=color)
            if reading:
                draw.text((part_x, 320), reading, font=ruby, fill=color)
            part_x += draw.textbbox((0, 0), base, font=main)[2]
        if item["romaji"]:
            box = draw.textbbox((0, 0), item["romaji"], font=romaji)
            draw.text((x + (width - (box[2] - box[0])) / 2, 495), item["romaji"], font=romaji, fill=color)
        x += width + gap
    centered(draw, 605, frame["caption"]["translationZh"], F(48), (245, 245, 245, 238))
    cards = frame["grammarCards"]
    total, gap, x = 1740, 12, 90
    widths = [total // len(cards)] * len(cards)
    widths[-1] += total - sum(widths)
    for item, width in zip(cards, widths):
        draw.rounded_rectangle((x, 705, x + width - gap, 950), 20, fill=CARD_FILL, outline=CARD_OUTLINE, width=2)
        center_x = x + (width - gap) / 2
        token = item["token"]
        box = draw.textbbox((0, 0), token, font=F(36))
        draw.text((center_x - (box[2] - box[0]) / 2, 730), token, font=F(36), fill="white")
        meaning_font = F(27)
        meaning_lines = wrap_card_text(draw, clean_display(item.get("functionZh", item["zhMeaning"])), meaning_font, width - gap - 24)
        for line_index, text in enumerate(meaning_lines):
            box = draw.textbbox((0, 0), text, font=meaning_font)
            draw.text((center_x - (box[2] - box[0]) / 2, 790 + line_index * 31), text, font=meaning_font, fill="white")
        pos = clean_display(item["posZh"])
        box = draw.textbbox((0, 0), pos, font=F(26))
        draw.text((center_x - (box[2] - box[0]) / 2, 875), pos, font=F(26), fill="white")
        x += width
    image.save(path)


concat = []
for index, (start, end, frame, active) in enumerate(frames):
    if end <= start:
        continue
    path = OVERLAYS / f"{index:04d}.png"
    render(frame, active, path)
    concat.extend((f"file '{path.as_posix()}'", f"duration {(end - start) / 1000:.3f}"))
concat.append(f"file '{(OVERLAYS / f'{len(frames) - 1:04d}.png').as_posix()}'")
concat_file = ROOT / "uchuu_v2_overlay.concat.txt"
concat_file.write_text("\n".join(concat), encoding="utf-8")
target = DELIVERABLES / "uchuu-qrc-composite-v2.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(BACKGROUND),
    "-f", "concat", "-safe", "0", "-i", str(concat_file), "-i", str(AUDIO),
    "-filter_complex", f"[1:v]format=rgba[ov];[0:v][ov]overlay=0:0:format=auto,format=yuv420p[v];[2:a]adelay={DELAY}:all=1[a]",
    "-map", "[v]", "-map", "[a]", "-r", "24000/1001", "-c:v", "libx264", "-crf", "18",
    "-c:a", "aac", "-b:a", "320k", "-shortest", str(target),
], check=True)
print(f"unmatched QRC frames: {unmatched}")
print(target)
