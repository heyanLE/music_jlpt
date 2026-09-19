#!/usr/bin/env python3
"""Render one lyric row as a finished still, for verification during review.

Usage
    python render_still.py PROJECT_ROOT FRAME_ID [OUTPUT] [--run-id ID] [--canvas 16x9]

The still is the real composite (background + foreground + floating spectrum) taken while
that row is on screen, so it shows exactly what the finished video will show.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_render import ProjectStill, load_renderer  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("frame_id")
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--run-id")
    parser.add_argument("--canvas", default="16x9")
    args = parser.parse_args()

    root = args.project_root.resolve()
    output = args.output or root / "deliverables" / "review" / f"{root.name}--line-{args.frame_id}.png"
    renderer = load_renderer(root)
    still = ProjectStill(root, run_id=args.run_id)
    info = still.still(renderer, args.frame_id, output)
    print(f"{info['frameId']} at {info['outputSeconds']}s -> {info['relativePath']}")


if __name__ == "__main__":
    main()
