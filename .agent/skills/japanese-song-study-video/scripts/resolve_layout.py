#!/usr/bin/env python3
"""Scale and validate study-current-v3 template geometry.

Usage: python resolve_layout.py TEMPLATE PALETTE OUTPUT --width 1920 --height 1080
"""
from __future__ import annotations

import argparse, json
from pathlib import Path


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    parser.add_argument("palette", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    args = parser.parse_args()
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("Canvas dimensions must be positive")
    template, palette = load(args.template), load(args.palette)
    if template.get("id") != "study-current-v3":
        raise SystemExit("This resolver supports study-current-v3 only")
    ref = template["canvas"]
    sx, sy = args.width / ref["referenceWidth"], args.height / ref["referenceHeight"]
    scale = min(sx, sy)
    def px(value: float, axis: str = "uniform") -> int:
        return round(value * ({"x": sx, "y": sy, "uniform": scale}[axis]))
    cover = template["cover"]["rectPx"]
    cards = template["cards"]["rectPx"]
    resolved = {
        "schemaVersion": 1,
        "templateId": template["id"],
        "canvas": {"width": args.width, "height": args.height, "fps": ref["fps"]},
        "scale": {"x": sx, "y": sy, "uniform": scale},
        "palette": palette,
        "font": template["font"],
        "cover": {"rectPx": [px(cover[0], "x"), px(cover[1], "y"), px(cover[2], "x"), px(cover[3], "y")]},
        "cards": {"rectPx": [px(cards[0], "x"), px(cards[1], "y"), px(cards[2], "x"), px(cards[3], "y")], "gapPx": px(template["cards"]["gapPx"]), "fieldLayout": template["cards"]["fieldLayout"]},
        "lyric": template["lyric"],
        "strokePx": {k: px(v) for k, v in template["strokePx"].items()},
        "constraints": {"meaningMaxLines": 2, "tokenMaxLines": 1, "grammarStructureMaxLines": 1, "cardsSingleRow": True}
    }
    x, y, w, h = resolved["cards"]["rectPx"]
    if x < 0 or y < 0 or x + w > args.width or y + h > args.height:
        raise SystemExit("Card rectangle is outside canvas")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(resolved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(args.output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
