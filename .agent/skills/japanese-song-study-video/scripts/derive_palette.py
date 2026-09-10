#!/usr/bin/env python3
"""Derive repeatable magic-color tokens from cover artwork.

Usage: python derive_palette.py COVER_IMAGE OUTPUT_JSON [--card-alpha 0.75]
"""
from __future__ import annotations

import argparse, colorsys, json
from collections import Counter
from pathlib import Path

from PIL import Image


def hex_rgb(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v))):02X}" for v in rgb)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("cover", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--card-alpha", type=float, default=0.75)
    a = p.parse_args()
    if not 0.70 <= a.card_alpha <= 0.80:
        raise SystemExit("--card-alpha must be in [0.70, 0.80]")

    image = Image.open(a.cover).convert("RGB").resize((160, 160))
    bins: Counter[tuple[int, int, int]] = Counter()
    for red, green, blue in image.getdata():
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
        if saturation < 0.36 or value < 0.18 or value > 0.94:
            continue
        bins[(round(red / 16) * 16, round(green / 16) * 16, round(blue / 16) * 16)] += 1
    if not bins:
        raise SystemExit("No saturated non-extreme pixels: choose palette manually")
    accent = max(bins, key=bins.get)
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in accent))
    active = colorsys.hsv_to_rgb(h, min(1.0, max(0.72, s)), min(1.0, max(0.92, v + 0.35)))
    body = colorsys.hsv_to_rgb(h, min(0.80, max(0.45, s)), max(0.28, min(0.58, v * 0.56)))
    out = {
        "schemaVersion": 1,
        "algorithm": "saturated-cover-pixel-hsv-v1",
        "cover": str(a.cover.resolve()),
        "accent": hex_rgb(accent),
        "activeTint": hex_rgb(tuple(c * 255 for c in active)),
        "body": hex_rgb(tuple(c * 255 for c in body)),
        "cardFill": {"color": hex_rgb(accent), "alpha": a.card_alpha},
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(a.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
