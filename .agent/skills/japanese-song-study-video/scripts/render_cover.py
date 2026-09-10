#!/usr/bin/env python3
"""Render the established Japanese-song-study platform cover layout.

Usage:
  python render_cover.py --cover COVER --palette PALETTE --config CONFIG
      --output-dir DIRECTORY --run-id YYYYMMDD [--report REPORT]

The fixed visual language is a large left/top artwork field, light information field,
thin magic-color rule, oversized dark text, and two benefit rows. It never emits
dark-gradient panels, bullets, cards, playback controls, or text outlines.
"""
from __future__ import annotations

import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = (Path(r"C:\Windows\Fonts\msyhbd.ttc"), Path(r"C:\Windows\Fonts\NotoSansCJK-Bold.ttc"))
DEFAULT_BENEFITS = ["歌词同步高亮", "假名注释", "罗马音", "逐词拆解"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def font_file() -> Path:
    from runtime_font import font_path
    return font_path()


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")[:6]
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


def fit_cover(image: Image.Image, rect: tuple[int, int, int, int], focus: str = "center"):
    x, y, width, height = rect; scale = max(width / image.width, height / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    if focus not in {"left", "center", "right"}:
        raise RuntimeError("artworkFocus must be left, center, or right")
    left = {"left": 0, "center": (image.width - width) // 2, "right": image.width - width}[focus]
    top = (image.height - height) // 2
    return image.crop((left, top, left + width, top + height)), (x, y)


def fitted_font(draw, text: str, path: Path, size: int, max_width: int, *, min_scale=.48):
    for current in range(size, max(1, round(size * min_scale)) - 1, -1):
        candidate = ImageFont.truetype(path, current)
        if draw.multiline_textbbox((0, 0), text, font=candidate, spacing=8)[2] <= max_width: return candidate
    raise RuntimeError(f"Text cannot fit: {text!r}")


def put(draw, xy, text: str, font, color, *, spacing=8):
    draw.multiline_text(xy, text, font=font, fill=color, spacing=spacing)
    return draw.multiline_textbbox(xy, text, font=font, spacing=spacing)


def colors(palette: dict):
    accent = rgb(palette["accent"])
    return accent, tuple(max(0, round(v * .27)) for v in accent), (255, 249, 250)


def benefit_rows(config: dict) -> tuple[str, str]:
    values = config["benefits"]
    if len(values) != 4: raise RuntimeError("benefits must contain exactly four values")
    return " · ".join(values[:2]), " · ".join(values[2:])


def draw_badge(canvas, draw, size, config, font_path, accent):
    """Draw an optional, explicitly enabled quality badge in the upper-right."""
    badge = config.get("badge")
    # No badge is the default; an empty object or a disabled badge must be inert.
    if not badge or not bool(badge.get("enabled", False)): return None
    width, height = size; scale = float(badge.get("scale", 1.0))
    asset = str(badge.get("asset", "")).strip()
    margin = round(min(width, height) * .032)
    if asset:
        logo = Image.open(asset).convert("RGBA")
        side = round(min(width, height) * .145 * scale)
        logo.thumbnail((side, side), Image.Resampling.LANCZOS)
        x, y = width - margin - logo.width, margin
        canvas.paste(logo, (x, y), logo)
        return (x, y, x + logo.width, y + logo.height)
    text = str(badge.get("text", "")).strip()
    if not text: return None
    fnt = ImageFont.truetype(font_path, round(min(width, height) * .037 * scale))
    box = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=4, align="center")
    pad_x, pad_y = round(width * .016), round(height * .012)
    badge_w, badge_h = (box[2] - box[0]) + pad_x * 2, (box[3] - box[1]) + pad_y * 2
    x, y = width - margin - badge_w, margin
    fill = rgb(str(badge["color"])) if badge.get("color") else accent
    draw.rounded_rectangle((x, y, x + badge_w, y + badge_h), radius=round(min(width, height) * .012), fill=fill)
    draw.multiline_text((x + pad_x - box[0], y + pad_y - box[1]), text, font=fnt, fill=(255, 255, 255), spacing=4, align="center")
    return (x, y, x + badge_w, y + badge_h)


def render_landscape(size, art, palette, config, font_path, focus):
    width, height = size; accent, ink, paper = colors(palette); art_width = round(width * .445)
    canvas = Image.new("RGB", size, paper); crop, pos = fit_cover(art, (0, 0, art_width, height), focus); canvas.paste(crop, pos)
    # Established horizontal cover geometry: a narrow gutter after the divider,
    # long header rule, and a short underline immediately below the benefit copy.
    draw = ImageDraw.Draw(canvas); divider_half = 6; x = art_width + divider_half + round(width * .004); usable = width - x - round(width * .025); bounds = {}
    draw.rectangle((art_width - 6, 0, art_width + 6, height), fill=accent)
    draw.rectangle((art_width + divider_half, round(height * .097), width - round(width * .025), round(height * .109)), fill=accent)
    bounds["series"] = put(draw, (x, round(height * .153)), config["series"], fitted_font(draw, config["series"], font_path, round(height * .10), usable), accent)
    title_font = fitted_font(draw, config["title"], font_path, round(height * .105), usable)
    bounds["title"] = put(draw, (x, round(height * .30)), config["title"], title_font, ink, spacing=6)
    subtitle = str(config.get("subtitle", "")).strip()
    artist_y = max(round(height * (.46 if subtitle else .50)), bounds["title"][3] + round(height * (.020 if subtitle else .045)))
    bounds["artist"] = put(draw, (x, artist_y), config["artist"], fitted_font(draw, config["artist"], font_path, round(height * .050), usable), ink)
    details_bottom = bounds["artist"][3]
    if subtitle:
        subtitle_y = details_bottom + round(height * .010)
        # Subtitles are a primary mobile-readable identifier.  Unless a project
        # explicitly overrides it, render them at twice the legacy base size.
        subtitle_scale = float(config.get("subtitleScale", 2.0))
        bounds["subtitle"] = put(draw, (x, subtitle_y), subtitle, fitted_font(draw, subtitle, font_path, round(height * .043 * subtitle_scale), usable), accent)
        details_bottom = bounds["subtitle"][3]
    row1, row2 = benefit_rows(config)
    benefits_y = max(round(height * (.69 if subtitle else .725)), details_bottom + round(height * (.018 if subtitle else .105)))
    bounds["benefitsRow1"] = put(draw, (x, benefits_y), row1, fitted_font(draw, row1, font_path, round(height * .060), usable), ink)
    bounds["benefitsRow2"] = put(draw, (x, benefits_y + round(height * .08)), row2, fitted_font(draw, row2, font_path, round(height * .060), usable), ink)
    underline_y = bounds["benefitsRow2"][3] + round(height * .025)
    underline_width = round(width * .21)
    if underline_y + round(height * .012) > height:
        raise RuntimeError("Landscape cover copy cannot fit above the underline")
    draw.rectangle((x, underline_y, x + underline_width, underline_y + round(height * .012)), fill=accent)
    bounds["benefitsUnderline"] = (x, underline_y, x + underline_width, underline_y + round(height * .012))
    badge_bounds = draw_badge(canvas, draw, size, config, font_path, accent)
    if badge_bounds: bounds["badge"] = badge_bounds
    return canvas, bounds


def render_portrait(size, art, palette, config, font_path, focus):
    width, height = size; accent, ink, paper = colors(palette); subtitle = str(config.get("subtitle", "")).strip(); art_height = round(height * (.34 if subtitle else .40)); margin = round(width * .075); usable = width - margin * 2
    canvas = Image.new("RGB", size, paper); crop, pos = fit_cover(art, (0, 0, width, art_height), focus); canvas.paste(crop, pos)
    draw = ImageDraw.Draw(canvas); bounds = {}; draw.rectangle((0, art_height - 6, width, art_height + 6), fill=accent)
    bounds["series"] = put(draw, (margin, art_height + round(height * (.045 if subtitle else .075))), config["series"], fitted_font(draw, config["series"], font_path, round(width * .11), usable), accent)
    bounds["title"] = put(draw, (margin, art_height + round(height * (.115 if subtitle else .145))), config["title"], fitted_font(draw, config["title"], font_path, round(width * .095), usable), ink, spacing=6)
    artist_y = max(art_height + round(height * (.23 if subtitle else .30)), bounds["title"][3] + round(height * (.022 if subtitle else .035)))
    bounds["artist"] = put(draw, (margin, artist_y), config["artist"], fitted_font(draw, config["artist"], font_path, round(width * .047), usable), ink)
    details_bottom = bounds["artist"][3]
    if subtitle:
        subtitle_y = details_bottom + round(height * .010)
        subtitle_scale = float(config.get("subtitleScale", 2.0))
        bounds["subtitle"] = put(draw, (margin, subtitle_y), subtitle, fitted_font(draw, subtitle, font_path, round(width * .040 * subtitle_scale), usable), accent)
        details_bottom = bounds["subtitle"][3]
    row1, row2 = benefit_rows(config)
    row1_font = fitted_font(draw, row1, font_path, round(width * .060), usable)
    row2_font = fitted_font(draw, row2, font_path, round(width * .060), usable)
    row1_box = draw.multiline_textbbox((0, 0), row1, font=row1_font, spacing=8)
    row2_box = draw.multiline_textbbox((0, 0), row2, font=row2_font, spacing=8)
    row_gap = round(height * (.008 if subtitle else .018))
    bottom_rule_y = round(height * .945)
    bottom_limit = bottom_rule_y - round(height * .010)
    # Use the actual glyph bounds, not font-size estimates: Pillow's glyph boxes
    # have a positive top offset, which otherwise makes the second row cross the rule.
    min_y = details_bottom - row1_box[1]
    desired_y = max(art_height + round(height * (.39 if subtitle else .43)), min_y)
    max_y = bottom_limit - row1_box[3] - row_gap - (row2_box[3] - row2_box[1])
    if max_y < min_y:
        raise RuntimeError("Portrait cover copy cannot fit above the bottom rule")
    y = min(desired_y, max_y)
    bounds["benefitsRow1"] = put(draw, (margin, y), row1, row1_font, ink)
    row2_y = bounds["benefitsRow1"][3] + row_gap - row2_box[1]
    bounds["benefitsRow2"] = put(draw, (margin, row2_y), row2, row2_font, ink)
    draw.rectangle((margin, bottom_rule_y, width - margin, round(height * .955)), fill=accent)
    badge_bounds = draw_badge(canvas, draw, size, config, font_path, accent)
    if badge_bounds: bounds["badge"] = badge_bounds
    return canvas, bounds


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--cover", type=Path, required=True); parser.add_argument("--palette", type=Path, required=True); parser.add_argument("--config", type=Path, required=True); parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--run-id", required=True); parser.add_argument("--report", type=Path)
    args = parser.parse_args(); config, palette = load_json(args.config), load_json(args.palette)
    for key in ("slug", "title", "artist", "outputs"):
        if not config.get(key): raise SystemExit(f"Missing config.{key}")
    config.setdefault("series", "快速学唱"); config.setdefault("benefits", DEFAULT_BENEFITS)
    if config.get("badge", {}).get("enabled", False) and config.get("badge", {}).get("asset"):
        config["badge"]["asset"] = str((args.config.parent / config["badge"]["asset"]).resolve())
    art = Image.open(args.cover).convert("RGB"); font = font_file(); args.output_dir.mkdir(parents=True, exist_ok=True); outputs = []
    for target in config["outputs"]:
        name, width, height = target["name"], int(target["width"]), int(target["height"]); focus = target.get("artworkFocus", "center")
        image, bounds = (render_landscape((width, height), art, palette, config, font, focus) if width >= height else render_portrait((width, height), art, palette, config, font, focus))
        if any(box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height for box in bounds.values()): raise SystemExit(f"Text overflow in {name}")
        output = args.output_dir / f"{config['slug']}--cover-{name}--{args.run_id}.png"; image.save(output, quality=95); outputs.append({"name": name, "path": str(output), "width": width, "height": height, "artworkFocus": focus, "bounds": bounds})
    if args.report:
        report = {"schemaVersion": 2, "renderer": "platform-cover-v1-established-layout", "font": str(font), "palette": palette, "outputs": outputs}
        args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); json.loads(args.report.read_text(encoding="utf-8"))


if __name__ == "__main__": main()
