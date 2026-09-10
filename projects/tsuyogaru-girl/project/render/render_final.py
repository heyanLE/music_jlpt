from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
PROJECT = ROOT / "project"
SOURCE = ROOT / "source"
RUN_ID = "20260818-final-r08"
WORK = PROJECT / "work" / RUN_ID
FINAL = ROOT / "deliverables" / "final"
W, H, FPS = 1920, 1080, 30
FONT_PATH = "C:/Windows/Fonts/msyhbd.ttc"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def f(size):
    return ImageFont.truetype(FONT_PATH, size)


def rgba(hex_color, alpha=255):
    c = hex_color.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def width(draw, value, font):
    return draw.textbbox((0, 0), value, font=font, stroke_width=0)[2]


def fit(draw, value, initial, limit, smallest=11):
    for size in range(initial, smallest - 1, -1):
        candidate = f(size)
        if width(draw, value, candidate) <= limit:
            return candidate
    raise ValueError(f"Card field cannot fit in one line: {value}")


def outlined(draw, xy, text, font, fill, stroke=3):
    draw.text(xy, text, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 235))


def char_spans(frame):
    caption = frame["caption"]
    text = caption["japanese"]
    qrc_text = caption.get("qrcJapanese", text)
    source_to_display = caption.get("sourceToDisplay")
    spans = []
    cursor = 0
    for part in frame["displayUnits"][0]["qrcParts"]:
        raw = part["text"]
        if raw:
            start = cursor
            cursor += len(raw)
            spans.append((part["startMs"], part["endMs"], start, cursor))
    if cursor != len(qrc_text):
        # Safe line fallback: show the whole line but do not highlight rather
        # than shifting any later source character.
        return []
    if source_to_display is None:
        return spans
    remapped = []
    for start_ms, end_ms, a, b in spans:
        targets = source_to_display[a:b]
        remapped.append((start_ms, end_ms, min(targets), max(targets) + 1))
    return remapped


def annotation_positions(text, annotations):
    result, used = [], {}
    for note in annotations:
        base = note.get("base", "")
        occurrence = note.get("occurrence")
        if not base or "reading" not in note:
            continue
        start = 0
        hits = []
        while True:
            hit = text.find(base, start)
            if hit < 0:
                break
            hits.append(hit)
            start = hit + len(base)
        index = (occurrence - 1) if occurrence else used.get(base, 0)
        if index < len(hits):
            result.append((hits[index], len(base), note["reading"]))
            used[base] = index + 1
    return result


def render_foreground(frame, active_span, palette, path):
    image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    # Foreground exists only during lyric segments; its veil is therefore lyric-only.
    draw.rectangle((0, 0, W, H), fill=(0, 0, 0, 71))
    # A single, quiet horizontal band keeps all four lyric layers readable on busy footage.
    foreground = load(PROJECT / "templates" / "foreground.json")
    lyric_backdrop = foreground.get("lyricBackdrop", {})
    if lyric_backdrop.get("enabled", False):
        x, y, band_w, band_h = lyric_backdrop["rectPx"]
        draw.rectangle((x, y, x + band_w, y + band_h), fill=rgba(lyric_backdrop["color"], round(255 * lyric_backdrop["opacity"])))
    cover = Image.open(SOURCE / "cover.jpg").convert("RGB").resize((220, 220), Image.Resampling.LANCZOS).convert("RGBA")
    image.alpha_composite(cover, (850, 35))

    text = frame["caption"]["japanese"]
    lyric_font, roma_font, furi_font, translation_font = f(70), f(34), f(28), f(45)
    gap = 9
    char_widths = [width(draw, char, lyric_font) for char in text]
    total = sum(char_widths) + gap * max(0, len(text) - 1)
    scale = min(1.0, (W * 0.90) / max(total, 1))
    if scale < 1:
        lyric_font, roma_font, furi_font = f(int(70 * scale)), f(max(18, int(34 * scale))), f(max(16, int(28 * scale)))
        char_widths = [width(draw, char, lyric_font) for char in text]
        total = sum(char_widths) + gap * max(0, len(text) - 1)
    x0 = (W - total) / 2
    xs, x = [], x0
    for char, char_w in zip(text, char_widths):
        xs.append(x)
        x += char_w + gap

    active_start, active_end = (-1, -1) if active_span is None else active_span
    active = rgba(palette["activeTint"])
    body = (255, 255, 255, 248)
    for i, char in enumerate(text):
        fill = active if active_start <= i < active_end else body
        outlined(draw, (xs[i], 360), char, lyric_font, fill)

    for start, length, reading in annotation_positions(text, frame["caption"].get("furigana", [])):
        anchor = xs[start]
        hit = active_start < start + length and active_end > start
        outlined(draw, (anchor, 320), reading, furi_font, active if hit else body, 2)

    # Romaji is placed token-by-token under the matching first token occurrence.
    token_cursor = 0
    for card in frame["grammarCards"]:
        token = card["token"]
        start = text.find(token, token_cursor)
        if start < 0:
            continue
        token_cursor = start + len(token)
        end = token_cursor
        token_w = (xs[end - 1] + char_widths[end - 1]) - xs[start]
        roma = card["romaji"]
        hit = active_start < end and active_end > start
        if card.get("sourceWord"):
            loan_font = f(23)
            loan = card["sourceWord"]
            outlined(draw, (xs[start] + (token_w - width(draw, loan, loan_font)) / 2, 320), loan, loan_font, active if hit else body, 2)
        outlined(draw, (xs[start] + (token_w - width(draw, roma, roma_font)) / 2, 485), roma, roma_font, active if hit else body, 2)

    translation = frame["caption"].get("translationZh", "")
    tw = width(draw, translation, translation_font)
    if tw > 1650:
        translation_font = fit(draw, translation, 45, 1650, 22)
        tw = width(draw, translation, translation_font)
    outlined(draw, ((W - tw) / 2, 595), translation, translation_font, body)

    cards = frame["grammarCards"]
    count = len(cards)
    cw = (1740 - (count - 1) * 12) / count
    card_fill = rgba(palette["cardFill"], 191)
    outline = rgba(palette["activeTint"], 190)
    for i, card in enumerate(cards):
        left = 90 + i * (cw + 12)
        draw.rounded_rectangle((left, 705, left + cw, 950), radius=20, fill=card_fill, outline=outline, width=2)
        fields = [
            (card["token"], 37, 730),
            (card.get("functionZh") or card.get("zhMeaning", ""), 26, 795),
            (card["posZh"], 25, 855),
        ]
        for value, size, top in fields:
            field_font = fit(draw, value, size, cw - 24)
            draw.text((left + (cw - width(draw, value, field_font)) / 2, top), value, font=field_font, fill=body, stroke_width=2, stroke_fill=(0, 0, 0, 230))
    image.save(path)


def main():
    frames = load(PROJECT / "frames.json")["frames"]
    manifest = load(PROJECT / "input-manifest.json")
    foreground = load(PROJECT / "templates" / "foreground.json")
    background = load(PROJECT / "templates" / "background.json")
    palette = load(PROJECT / "palette.json")
    decision = load(PROJECT / "review" / "review-decision.json")
    if decision["content"] != "approved":
        raise RuntimeError("Unapproved content")
    if sha(PROJECT / "frames.json") != decision["frameSha256"]:
        raise RuntimeError("frames.json changed after content approval")
    WORK.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)
    hashes = {str(path.relative_to(ROOT)): sha(path) for path in [SOURCE / "background.mp4", SOURCE / "music.flac", SOURCE / "cover.jpg", PROJECT / "frames.json", PROJECT / "templates" / "foreground.json", PROJECT / "templates" / "background.json"]}
    authorization = {"userWording": "确认，先试试", "createdAt": datetime.now(timezone.utc).isoformat(), "frameSha256": sha(PROJECT / "frames.json"), "sourceAndTemplateSha256": hashes}
    dump(PROJECT / "render" / "render-authorization.json", authorization)
    duration_ms = manifest["assets"]["music"]["durationMs"]
    output = FINAL / f"tsuyogaru-girl--study-current-v2--16x9--{RUN_ID}.mp4"
    dump(PROJECT / "render" / "render-plan.json", {"runId": RUN_ID, "canvas": [W, H], "fps": FPS, "audioClock": "music.flac", "durationMs": duration_ms, "foregroundVisibility": manifest["foregroundVisibility"], "background": background, "foregroundTemplateSha256": sha(PROJECT / "templates" / "foreground.json"), "output": str(output), "matching": "full frozen QM source-character mapping; fallback disables highlight"})

    blank = WORK / "blank.png"
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    entries, cursor, index, held_foreground = [], 0, 0, None
    persist_from_ms = background["segments"][1]["startMs"]
    def append_gap(start_ms, end_ms):
        if end_ms <= start_ms:
            return
        if manifest["foregroundVisibility"] != "lyric-only-before-gaussian-then-persistent" or held_foreground is None:
            entries.append((blank, end_ms - start_ms))
        elif end_ms <= persist_from_ms:
            entries.append((blank, end_ms - start_ms))
        elif start_ms < persist_from_ms:
            entries.append((blank, persist_from_ms - start_ms))
            entries.append((held_foreground, end_ms - persist_from_ms))
        else:
            entries.append((held_foreground, end_ms - start_ms))
    for frame in frames:
        if cursor < frame["startMs"]:
            append_gap(cursor, frame["startMs"])
        spans = char_spans(frame)
        local = frame["startMs"]
        for start_ms, end_ms, a, b in spans:
            if start_ms > local:
                p = WORK / f"fg-{index:04d}.png"; render_foreground(frame, None, palette, p); entries.append((p, start_ms - local)); index += 1
            if end_ms > start_ms:
                p = WORK / f"fg-{index:04d}.png"; render_foreground(frame, (a, b), palette, p); entries.append((p, end_ms - start_ms)); index += 1
            local = max(local, end_ms)
        # A neutral state is retained through an interlude instead of clearing the foreground.
        held_foreground = WORK / f"fg-hold-{index:04d}.png"
        render_foreground(frame, None, palette, held_foreground)
        index += 1
        if local < frame["endMs"]:
            entries.append((held_foreground, frame["endMs"] - local))
        cursor = max(cursor, frame["endMs"])
    if cursor < duration_ms:
        append_gap(cursor, duration_ms)
    concat = WORK / "foreground.concat.txt"
    concat.write_text("\n".join([f"file '{path.as_posix()}'\nduration {ms / 1000:.3f}" for path, ms in entries] + [f"file '{blank.as_posix()}'"]), encoding="utf-8", newline="\n")
    after_seconds = background["segments"][0]["endMs"] / 1000
    transition_seconds = background["transition"]["durationMs"] / 1000
    transition_start = background["transition"]["startsMs"] / 1000
    tail_seconds = duration_ms / 1000 - after_seconds + transition_seconds
    cover_bg = WORK / "cover-gaussian.jpg"
    base = Image.open(SOURCE / "cover.jpg").convert("RGB").resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(30))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * background["segments"][1]["darkOverlayOpacity"])))
    base_rgba = base.convert("RGBA")
    base_rgba.alpha_composite(shade)
    base_rgba.convert("RGB").save(cover_bg, quality=95)
    spectrum = background["spectrumOverlay"]
    spectrum_y = spectrum["placement"]["yPx"]
    alpha = spectrum["alpha"]
    subprocess.run([sys.executable, str(PROJECT / "render" / "build_foobar_spectrum.py"), "--work", str(WORK)], check=True)
    spectrum_video = WORK / "foobar-spectrum.mp4"
    filters = f"[0:v]trim=duration={after_seconds},setpts=PTS-STARTPTS,scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,fps={FPS}[v0];[2:v]trim=duration={tail_seconds},setpts=PTS-STARTPTS,fps={FPS}[v1];[v0][v1]xfade=transition=fade:duration={transition_seconds}:offset={transition_start}[bg];[1:v]fps={FPS},format=rgba[fg];[bg][fg]overlay=0:0:format=auto[composite];[4:v]format=rgba,colorkey=black:similarity=0.05:blend=0.04,colorchannelmixer=aa={alpha}[spec];[composite][spec]overlay=(W-w)/2:{spectrum_y}:format=auto,fps={FPS},format=yuv420p[v]"
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(SOURCE / "background.mp4"), "-f", "concat", "-safe", "0", "-i", str(concat), "-loop", "1", "-i", str(cover_bg), "-i", str(SOURCE / "music.flac"), "-i", str(spectrum_video), "-filter_complex", filters, "-map", "[v]", "-map", "3:a:0", "-t", f"{duration_ms / 1000:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True)
    print(output)


if __name__ == "__main__":
    main()
