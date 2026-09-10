"""Render the approved static previous/current/next lyric foreground.

Inputs are source/background.mp4, source/music.flac, project/frames.json and the
project palette.  No pixels are taken from a previously rendered master.
"""
import json
import math
import argparse
import subprocess
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SKILL = Path("C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts")
sys.path.insert(0, str(SKILL))
from render_video import ForegroundRenderer, rgb

OUT = ROOT / "project" / "work" / "horizontal-rail-clean-preview"
W, H, FPS = 1920, 1080, 30
START_MS, END_MS, SHIFT_MS = 13200, 24400, 480
BODY = (255, 255, 255, 242)
MUTED = (255, 255, 255, 145)


def ease_out_cubic(value):
    value = max(0.0, min(1.0, value))
    return 1.0 - (1.0 - value) ** 3


def spans(frame):
    text = frame["caption"]["japanese"]
    result, cursor = [], 0
    for card in frame.get("_annotationCards", frame.get("grammarCards", [])):
        start = text.find(card["token"], cursor)
        if start < 0:
            result.append(None)
        else:
            result.append((start, start + len(card["token"])))
            cursor = start + len(card["token"])
    return result


def active_character(frame, now):
    offset = 0
    for unit in frame.get("displayUnits", []):
        for part in unit.get("qrcParts", []):
            end = offset + len(part["text"])
            if part["startMs"] <= now < part["endMs"]:
                return offset, end
            offset = end
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-ms", type=int, default=START_MS)
    parser.add_argument("--end-ms", type=int, default=END_MS)
    parser.add_argument("--foreground-mov")
    parser.add_argument("--static-neighbors", action="store_true")
    args = parser.parse_args()
    start_ms, end_ms = args.start_ms, args.end_ms
    OUT.mkdir(parents=True, exist_ok=True)
    renderer = ForegroundRenderer(ROOT, W, H)
    # Keep every sung occurrence for lyric/romaji anchoring, but show each
    # identical token only once in the grammar-card row.
    for reviewed_frame in renderer.frames.values():
        all_cards = reviewed_frame.get("grammarCards", [])
        reviewed_frame["_annotationCards"] = all_cards
        seen_tokens = {}
        unique_cards = []
        old_to_new = {}
        for old_index, card in enumerate(all_cards):
            if card["token"] in seen_tokens:
                old_to_new[old_index] = seen_tokens[card["token"]]
                continue
            new_index = len(unique_cards)
            seen_tokens[card["token"]] = new_index
            old_to_new[old_index] = new_index
            unique_cards.append(card)
        reviewed_frame["grammarCards"] = unique_cards
        for ruby in reviewed_frame.get("caption", {}).get("furigana", []):
            ruby["cardIndex"] = old_to_new.get(int(ruby["cardIndex"]), int(ruby["cardIndex"]))
    ordered = sorted(renderer.frames.values(), key=lambda item: item["startMs"])
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    jp_font, ro_font = renderer.font(70), renderer.font(34)
    countdown_font = renderer.font(82)
    widths = [max(700, math.ceil(max(
        probe.textlength(f["caption"]["japanese"], font=jp_font),
        probe.textlength(f["caption"].get("romaji", ""), font=ro_font))) + 80) for f in ordered]
    centers, cursor = [], 0.0
    for width in widths:
        centers.append(cursor + width / 2)
        cursor += width + 56

    veil_alpha = round(float(renderer.presentation.get("veil", {}).get("opacity", .28)) * 255)
    veil = rgb(renderer.presentation.get("veil", {}).get("color", "#000000")) + (veil_alpha,)
    active_color = rgb(renderer.palette["activeTint"]) + (255,)
    cover = renderer.cover.resize((220, 220), Image.Resampling.LANCZOS)
    count = math.ceil((end_ms - start_ms) * FPS / 1000)
    encoder = None
    if args.foreground_mov:
        encoder = subprocess.Popen([
            "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo",
            "-pixel_format", "rgba", "-video_size", f"{W}x{H}", "-framerate", str(FPS),
            "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", args.foreground_mov
        ], stdin=subprocess.PIPE)

    for number in range(count):
        scratch = OUT / f".scratch-{os.getpid()}-{number:05d}.png"
        now = start_ms + number * 1000 / FPS
        current = max(0, next((i - 1 for i, f in enumerate(ordered) if f["startMs"] > now), len(ordered) - 1))
        frame = ordered[current]
        next_start = ordered[current + 1]["startMs"] if current + 1 < len(ordered) else end_ms
        # Persistent foreground mode: show the first reviewed line throughout
        # the prelude, hold each line until the next hard QRC switch, and keep
        # the final reviewed line through the output tail.
        foreground_visible = True
        renderer.render(frame["id"] if foreground_visible else None, None, scratch, cover_visible=False)
        with Image.open(scratch) as source_image:
            image = source_image.convert("RGBA").copy()
        scratch.unlink(missing_ok=True)
        if not foreground_visible:
            if encoder:
                encoder.stdin.write(image.tobytes())
            else:
                image.save(OUT / f"foreground-{number:04d}.png")
            continue
        # Repaint only the cover and main sentence bands with the same global veil.
        veil_layer = Image.new("RGBA", image.size, veil)
        image.paste(veil_layer.crop((0, 0, W, 275)), (0, 0))
        image.paste(veil_layer.crop((0, 275, W, 480)), (0, 275))
        image.alpha_composite(cover, (850, 35))  # exact hoshi-furu-umi geometry

        next_i = min(current + 1, len(ordered) - 1)
        if not args.static_neighbors and next_i != current and ordered[next_i]["startMs"] - SHIFT_MS <= now < ordered[next_i]["startMs"]:
            progress = ease_out_cubic((now - (ordered[next_i]["startMs"] - SHIFT_MS)) / SHIFT_MS)
            rail_center = centers[current] + (centers[next_i] - centers[current]) * progress
        else:
            rail_center = centers[current]

        rail = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(rail)
        # Clip exactly at the physical canvas edges so the rail appears to
        # continue beyond the video rather than ending at an inset viewport.
        viewport_left, viewport_right = 0, W
        for index in range(max(0, current - 2), min(len(ordered), current + 3)):
            item = ordered[index]
            x = W / 2 + centers[index] - rail_center
            if x + widths[index] / 2 < viewport_left or x - widths[index] / 2 > viewport_right:
                continue
            text = item["caption"]["japanese"]
            text_w = draw.textlength(text, font=jp_font)
            text_x = x - text_w / 2
            base_fill = BODY if index == current else MUTED
            active_span = active_character(item, now) if index == current else None
            card_spans = spans(item)

            cx = text_x
            for char_index, char in enumerate(text):
                fill = active_color if active_span and active_span[0] <= char_index < active_span[1] else base_fill
                renderer.outlined(draw, (cx, 330), char, jp_font, fill, 4)
                cx += draw.textlength(char, font=jp_font)

            ruby_font = renderer.font(28)
            for ruby in item["caption"].get("furigana", []):
                start = int(ruby.get("start", ruby.get("baseStart", ruby.get("tokenStart", 0))))
                end = int(ruby.get("end", start + len(ruby.get("base", ""))))
                ruby_active = bool(active_span and start < active_span[1] and active_span[0] < end)
                rx = text_x + draw.textlength(text[:start], font=jp_font)
                renderer.outlined(draw, (rx, 295), ruby["reading"], ruby_font,
                                  active_color if ruby_active else base_fill, 2)

            for card_index, card in enumerate(item.get("_annotationCards", item.get("grammarCards", []))):
                span = card_spans[card_index]
                if not span:
                    continue
                start, end = span
                block_active = bool(active_span and start < active_span[1] and active_span[0] < end)
                fill = active_color if block_active else base_fill
                token_x = text_x + draw.textlength(text[:start], font=jp_font)
                token_w = draw.textlength(text[start:end], font=jp_font)
                if card.get("sourceWord"):
                    source_font = renderer.font(23)
                    sw = draw.textlength(card["sourceWord"], font=source_font)
                    renderer.outlined(draw, (token_x + (token_w - sw) / 2, 295), card["sourceWord"], source_font, fill, 2)
                if card.get("romaji"):
                    rw = draw.textlength(card["romaji"], font=ro_font)
                    renderer.outlined(draw, (token_x + (token_w - rw) / 2, 430), card["romaji"], ro_font, fill, 2)

            clipped = rail.crop((viewport_left, 275, viewport_right, 480))
            image.alpha_composite(clipped, (viewport_left, 275))
        first_start = ordered[0]["startMs"]
        if first_start - 3000 <= now < first_start:
            remaining = max(1, min(3, math.ceil((first_start - now) / 1000)))
            countdown_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            countdown_draw = ImageDraw.Draw(countdown_layer)
            countdown_draw.ellipse((1685, 65, 1805, 185), fill=(0, 0, 0, 150), outline=active_color, width=4)
            value = str(remaining)
            box = countdown_draw.textbbox((0, 0), value, font=countdown_font, stroke_width=4)
            tw, th = box[2] - box[0], box[3] - box[1]
            renderer.outlined(countdown_draw, (1745 - tw / 2, 125 - th / 2 - box[1]), value,
                              countdown_font, active_color, 4)
            image.alpha_composite(countdown_layer)
        if encoder:
            encoder.stdin.write(image.tobytes())
        else:
            image.save(OUT / f"foreground-{number:04d}.png")

    if encoder:
        encoder.stdin.close()
        if encoder.wait() != 0:
            raise RuntimeError("Foreground qtrle encoder failed")
    (OUT / "preview.json").write_text(json.dumps({
        "sourceVideo": "five-scene custom timeline", "sourceAudio": "source/music.mp3",
        "content": "project/frames.json", "startMs": start_ms, "endMs": end_ms,
        "fps": FPS, "coverRectPx": [850, 35, 220, 220], "shiftMs": SHIFT_MS,
        "sentenceGapPx": 56, "renderMethod": "clean-source-composition"
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
