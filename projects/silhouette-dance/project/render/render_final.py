from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\project\musicjlpt\projects\silhouette-dance")
PROJECT, SOURCE = ROOT / "project", ROOT / "source"
RUN_ID = "20260819-final-native-fps-v4-no-spectrum"
WORK, FINAL = PROJECT / "work" / RUN_ID, ROOT / "deliverables" / "final"
W, H, FPS = 1920, 1080, "24000/1001"
FONT = "C:/Windows/Fonts/msyhbd.ttc"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size):
    return ImageFont.truetype(FONT, max(9, int(size)))


def rgba(color, alpha=255):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def tw(draw, text, ft):
    return draw.textbbox((0, 0), text, font=ft, stroke_width=0)[2]


def fit(draw, text, size, maximum, minimum=10):
    for candidate in range(size, minimum - 1, -1):
        ft = font(candidate)
        if tw(draw, text, ft) <= maximum:
            return ft
    return font(minimum)


def wrap2(draw, text, size, maximum):
    # CJK strings have no reliable whitespace word boundaries; measure characters.
    for candidate in range(size, 9, -1):
        ft = font(candidate)
        lines, current = [], ""
        for char in text:
            if tw(draw, current + char, ft) <= maximum:
                current += char
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
        if len(lines) <= 2:
            return ft, lines
    raise ValueError(f"Card meaning cannot fit two lines: {text}")


def outlined(draw, xy, text, ft, fill, stroke):
    draw.text(xy, text, font=ft, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 238))


def is_kanji(ch):
    return "\u3400" <= ch <= "\u9fff" or ch == "々"


def to_hiragana(value):
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


def kanji_run_readings(token, reading):
    """Map the stored token reading to only its kanji runs.

    The stored reading is verified against QQ Music's timed romaji; unlike a
    general-purpose kanji converter, it preserves lyric-specific readings.
    """
    token, reading = to_hiragana(token), to_hiragana(reading)
    result, char_at, reading_at = [], 0, 0
    while char_at < len(token):
        if not is_kanji(token[char_at]):
            literal_start = char_at
            while char_at < len(token) and not is_kanji(token[char_at]):
                char_at += 1
            literal = token[literal_start:char_at]
            if reading.startswith(literal, reading_at):
                reading_at += len(literal)
            else:
                found = reading.find(literal, reading_at)
                if found < 0:
                    return []
                reading_at = found + len(literal)
            continue
        run_start = char_at
        while char_at < len(token) and is_kanji(token[char_at]):
            char_at += 1
        next_literal_start = char_at
        while char_at < len(token) and not is_kanji(token[char_at]):
            char_at += 1
        next_literal = token[next_literal_start:char_at]
        next_at = reading.find(next_literal, reading_at) if next_literal else len(reading)
        if next_at < reading_at:
            return []
        result.append((run_start, next_literal_start, reading[reading_at:next_at]))
        reading_at = next_at
        # The next loop consumes this literal and advances the reading cursor.
        char_at = next_literal_start
    return result


def token_positions(text, cards):
    result, cursor = [], 0
    for card in cards:
        token = card["token"]
        start = text.find(token, cursor)
        if start < 0:
            start = text.find(token)
        if start < 0:
            continue
        result.append((card, start, start + len(token)))
        cursor = start + len(token)
    return result


def spans(frame):
    parts = frame["displayUnits"][0].get("qrcParts", [])
    original = "".join(item["text"] for item in parts)
    text = frame["caption"]["japanese"]
    if original != text:
        return []
    out, at = [], 0
    for item in parts:
        end = at + len(item["text"])
        out.append((item["startMs"], item["startMs"] + item["durationMs"], at, end))
        at = end
    return out


def draw_foreground(frame, active, palette, output):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, W, H), fill=(0, 0, 0, round(255 * 0.28)))
    cover = Image.open(SOURCE / "cover.jpg").convert("RGB").resize((220, 220), Image.Resampling.LANCZOS).convert("RGBA")
    image.alpha_composite(cover, (850, 35))
    text = frame["caption"]["japanese"]
    cards = frame.get("grammarCards", [])
    jp_ft, roma_ft, furi_ft, cn_ft = font(70), font(34), font(28), font(45)
    gap = 9
    widths = [tw(draw, c, jp_ft) for c in text]
    total = sum(widths) + gap * max(0, len(text) - 1)
    if total > W * 0.90:
        scale = (W * 0.90) / total
        jp_ft, roma_ft, furi_ft = font(70 * scale), font(34 * scale), font(28 * scale)
        widths = [tw(draw, c, jp_ft) for c in text]
        total = sum(widths) + gap * max(0, len(text) - 1)
    x, xs = (W - total) / 2, []
    for char, width in zip(text, widths):
        xs.append(x); x += width + gap
    active_a, active_b = (-1, -1) if active is None else active
    body, hi = (255, 255, 255, 250), rgba(palette["activeTint"])
    for index, char in enumerate(text):
        outlined(draw, (xs[index], 330), char, jp_ft, hi if active_a <= index < active_b else body, 4)
    for card, start, end in token_positions(text, cards):
        # Furigana only sits on contiguous kanji runs; literal kana remains unannotated.
        for local_start, local_end, reading in kanji_run_readings(card["token"], card.get("reading", "")):
            i, j = start + local_start, start + local_end
            if reading:
                outlined(draw, (xs[i], 295), reading, furi_ft, hi if active_a < j and active_b > i else body, 2)
        token_w = xs[end - 1] + widths[end - 1] - xs[start]
        if card.get("sourceWord"):
            sf = font(23); value = card["sourceWord"]
            outlined(draw, (xs[start] + (token_w - tw(draw, value, sf)) / 2, 295), value, sf, hi if active_a < end and active_b > start else body, 2)
        roma = card.get("romaji", "")
        if roma:
            outlined(draw, (xs[start] + (token_w - tw(draw, roma, roma_ft)) / 2, 430), roma, roma_ft, hi if active_a < end and active_b > start else body, 2)
    translation = frame["caption"].get("translationZh", "")
    if translation:
        cn_ft = fit(draw, translation, 45, 1650, 22)
        outlined(draw, ((W - tw(draw, translation, cn_ft)) / 2, 500), translation, cn_ft, body, 3)
    if cards:
        count, left, width_total, card_y, card_h, gap_card = len(cards), 95, 1730, 600, 250, 12
        card_w = (width_total - (count - 1) * gap_card) / count
        for index, card in enumerate(cards):
            x0 = left + index * (card_w + gap_card)
            draw.rounded_rectangle((x0, card_y, x0 + card_w, card_y + card_h), radius=20, fill=rgba(palette["cardFill"]["color"], 128), outline=rgba(palette["activeTint"], 205), width=2)
            token_ft = fit(draw, card["token"], 37, card_w - 26, 14)
            outlined(draw, (x0 + (card_w - tw(draw, card["token"], token_ft)) / 2, 625), card["token"], token_ft, body, 2)
            meaning = card.get("functionZh") or card.get("zhMeaning", "")
            meaning_ft, lines = wrap2(draw, meaning, 26, card_w - 26)
            top = 695 if len(lines) == 1 else 678
            for row, line in enumerate(lines):
                outlined(draw, (x0 + (card_w - tw(draw, line, meaning_ft)) / 2, top + row * 32), line, meaning_ft, body, 2)
            pos_ft = fit(draw, card["posZh"], 25, card_w - 26, 12)
            outlined(draw, (x0 + (card_w - tw(draw, card["posZh"], pos_ft)) / 2, 770), card["posZh"], pos_ft, body, 2)
    image.save(output)


def main():
    dependency_dir = str(PROJECT / "work" / "draft-deps")
    os.environ["PYTHONPATH"] = dependency_dir
    if dependency_dir not in sys.path:
        sys.path.insert(0, dependency_dir)
    frames = load(PROJECT / "frames.json")["frames"]
    manifest, palette = load(PROJECT / "input-manifest.json"), load(PROJECT / "palette.json")
    decision = load(PROJECT / "review" / "review-decision.json")
    if decision["content"] != "approved" or sha(PROJECT / "frames.json") != decision["frameSha256"]:
        raise RuntimeError("Current frames do not have approved review content")
    WORK.mkdir(parents=True, exist_ok=True); FINAL.mkdir(parents=True, exist_ok=True)
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in [SOURCE / "background-mv.mp4", SOURCE / "music.flac", SOURCE / "cover.jpg", PROJECT / "frames.json", PROJECT / "presentation.json", PROJECT / "scene-timeline.json", PROJECT / "palette.json", PROJECT / "templates" / "foreground.json"]}
    authorization = {"userWording": "\u786e\u8ba4\u6e32\u67d3", "createdAt": datetime.now(timezone.utc).isoformat(), "frameSha256": sha(PROJECT / "frames.json"), "sourceAndTemplateSha256": hashes}
    dump(PROJECT / "render" / "render-authorization.json", authorization)
    duration_ms = 209453
    output = FINAL / f"silhouette-dance--study-current-v3--16x9--{RUN_ID}.mkv"
    dump(PROJECT / "render" / "render-plan.json", {"runId": RUN_ID, "output": str(output), "canvas": [W, H], "fps": FPS, "audioClock": "source/music.flac", "durationMs": duration_ms, "foreground": "fresh transparent PNG state per QRC unit; lyric-only veil", "background": "source/background-mv.mp4, height-center-pillarbox, source audio muted", "hashes": hashes, "matching": "full exact QRC text only; unmatched rows render neutral foreground without token highlight"})
    blank = WORK / "blank.png"; Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    entries, cursor, counter = [], 0, 0
    for frame in frames:
        if frame["startMs"] > cursor:
            entries.append((blank, frame["startMs"] - cursor))
        sequence, local = spans(frame), frame["startMs"]
        if not sequence:
            path = WORK / f"fg-{counter:04d}.png"; draw_foreground(frame, None, palette, path); counter += 1
            entries.append((path, frame["endMs"] - frame["startMs"]))
        else:
            for start, end, a, b in sequence:
                if start > local:
                    path = WORK / f"fg-{counter:04d}.png"; draw_foreground(frame, None, palette, path); counter += 1
                    entries.append((path, start - local))
                if end > start:
                    path = WORK / f"fg-{counter:04d}.png"; draw_foreground(frame, (a, b), palette, path); counter += 1
                    entries.append((path, end - start))
                local = end
            if local < frame["endMs"]:
                path = WORK / f"fg-{counter:04d}.png"; draw_foreground(frame, None, palette, path); counter += 1
                entries.append((path, frame["endMs"] - local))
        cursor = frame["endMs"]
    if cursor < duration_ms:
        entries.append((blank, duration_ms - cursor))
    concat = WORK / "foreground.concat.txt"
    concat.write_text("\n".join([f"file '{p.as_posix()}'\nduration {ms / 1000:.3f}" for p, ms in entries] + [f"file '{entries[-1][0].as_posix()}'"]), encoding="utf-8", newline="\n")
    filt = f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih):color=black,fps={FPS},setpts=PTS-STARTPTS[bg];[1:v]fps={FPS},format=rgba[fg];[bg][fg]overlay=0:0:format=auto,fps={FPS},format=yuv420p[v]"
    command = ["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(SOURCE / "background-mv.mp4"), "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(SOURCE / "music.flac"), "-filter_complex", filt, "-map", "[v]", "-map", "2:a:0", "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", FPS, "-fps_mode", "cfr", "-c:a", "flac", "-map_metadata", "-1", str(output)]
    subprocess.run(command, check=True)
    print(output)


if __name__ == "__main__":
    main()
