"""Render a disposable UX preview for a horizontally sliding lyric rail.

This does not modify frames.json, presentation.json, render authorization, or the
delivered master.  It masks only the old top preview strip of the approved video.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "project" / "work" / "horizontal-rail-preview"
W, H, FPS = 960, 540, 30
CLIP_START_MS, CLIP_END_MS = 13200, 24400
TRANSITION_MS = 480


def font(size):
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc"),
        Path("C:/Windows/Fonts/meiryob.ttc"),
        Path("C:/Windows/Fonts/YuGothB.ttc"),
    ]
    return ImageFont.truetype(str(next(p for p in candidates if p.exists())), size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def outlined(draw, xy, text, fnt, fill, stroke=2, anchor=None):
    draw.text(xy, text, font=fnt, fill=fill, stroke_width=stroke,
              stroke_fill=(0, 0, 0, 245), anchor=anchor)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = json.loads((ROOT / "project" / "frames.json").read_text(encoding="utf-8"))["frames"]
    cover = Image.open(ROOT / "source" / "cover.jpg").convert("RGB").resize((76, 76), Image.Resampling.LANCZOS)
    jp_font, ro_font, ruby_font = font(34), font(18), font(14)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widths = [max(350, math.ceil(max(
        measure.textlength(f["caption"]["japanese"], font=jp_font),
        measure.textlength(f["caption"].get("romaji", ""), font=ro_font))) + 40) for f in frames]
    centers = []
    cursor = 0.0
    for width in widths:
        centers.append(cursor + width / 2)
        cursor += width + 28

    total_frames = math.ceil((CLIP_END_MS - CLIP_START_MS) * FPS / 1000)
    for n in range(total_frames):
        now = CLIP_START_MS + n * 1000 / FPS
        current = max(0, next((i - 1 for i, f in enumerate(frames) if f["startMs"] > now), len(frames) - 1))
        next_i = min(current + 1, len(frames) - 1)
        next_start = frames[next_i]["startMs"]
        if next_i != current and next_start - TRANSITION_MS <= now < next_start:
            p = ease((now - (next_start - TRANSITION_MS)) / TRANSITION_MS)
            rail_center = centers[current] + (centers[next_i] - centers[current]) * p
        else:
            rail_center = centers[current]

        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # The compositor restores this region from the clean source background.
        # Continue the existing foreground-wide 0.28 veil across that restored area;
        # this is not a lyric-local mask.
        d.rectangle((0, 0, W, 247), fill=(0, 0, 0, 71))
        # Match the template's vertical cover anchor (35 px at 1080p) and center it.
        im.alpha_composite(cover.convert("RGBA"), ((W - 76) // 2, 17))
        viewport_left, viewport_right = 38, W - 38
        for i in range(max(0, current - 2), min(len(frames), current + 3)):
            x = W / 2 + centers[i] - rail_center
            if x + widths[i] / 2 < viewport_left or x - widths[i] / 2 > viewport_right:
                continue
            alpha = 255 if i == current else 150
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            text = frames[i]["caption"]["japanese"]
            text_w = ld.textlength(text, font=jp_font)
            text_x = x - text_w / 2
            # Current-line QRC character highlight remains attached to the moving rail.
            qrc = [p for u in frames[i].get("displayUnits", []) for p in u.get("qrcParts", [])]
            char_x = text_x
            for char_index, char in enumerate(text):
                fill = (255, 255, 255, alpha)
                if i == current and char_index < len(qrc) and qrc[char_index]["startMs"] <= now < qrc[char_index]["endMs"]:
                    fill = (255, 230, 56, 255)
                outlined(ld, (char_x, 178), char, jp_font, fill, 2, "lm")
                char_x += ld.textlength(char, font=jp_font)
            for ruby in frames[i]["caption"].get("furigana", []):
                rx = text_x + ld.textlength(text[:ruby["start"]], font=jp_font)
                outlined(ld, (rx, 145), ruby["reading"], ruby_font,
                         (255, 255, 255, alpha), 1, "lm")
            outlined(ld, (x, 223), frames[i]["caption"].get("romaji", ""), ro_font,
                     (225, 232, 242, alpha), 1, "mm")
            # Crop the continuous rail at both sides.
            cropped = layer.crop((viewport_left, 139, viewport_right, 247))
            im.alpha_composite(cropped, (viewport_left, 139))
        im.save(OUT / f"rail-{n:04d}.png")

    meta = {"clipStartMs": CLIP_START_MS, "clipEndMs": CLIP_END_MS,
            "fps": FPS, "frames": total_frames, "transitionMs": TRANSITION_MS,
            "note": "Disposable visual prototype; approved source data is untouched."}
    (OUT / "preview.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
