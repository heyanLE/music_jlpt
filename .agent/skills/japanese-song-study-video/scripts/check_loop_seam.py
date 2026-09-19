#!/usr/bin/env python3
"""Report what the foreground is doing at each background loop seam.

A looping background restarts mid-output, and whether that lands inside a lyric
line is a property of the project, not of ffmpeg. This records the seam times,
the foreground state at each one, representative stills and a contact sheet so the
behaviour can be accepted knowingly instead of discovered in the finished video.

Usage
    python check_loop_seam.py PROJECT_ROOT [--timeline FILE] [--run-id ID] [--report FILE] [--no-stills]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preview_render import ProjectStill, extract, load, write_json  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is a documented requirement
    Image = None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--no-stills", action="store_true")
    parser.add_argument("--columns", type=int, default=2)
    args = parser.parse_args()

    root = args.project_root.resolve()
    still = ProjectStill(root, timeline_path=args.timeline, run_id=args.run_id)
    timeline = still.require_timeline()
    manifest = load(root / "project" / "input-manifest.json")
    scene = load(root / "project" / "scene-timeline.json")["segments"][0]
    duration_ms = int(timeline["durationMs"])
    video_seconds = still.video_seconds

    seams = []
    loop = 1
    while True:
        seam_ms = round(loop * video_seconds * 1000)
        if seam_ms >= duration_ms:
            break
        segment = next((item for item in timeline["segments"]
                        if item["startMs"] <= seam_ms < item["endMs"]), None)
        seams.append({
            "seamIndex": loop,
            "outputMs": seam_ms,
            "outputSeconds": round(seam_ms / 1000, 3),
            "foregroundState": None if segment is None else {
                key: value for key, value in segment.items()
                if key in ("kind", "frameId", "activePartIndex", "countdownValue")
            },
            "insideLyric": bool(segment and segment["kind"] == "active"),
        })
        loop += 1

    contact = None
    if not args.no_stills:
        qa_dir = root / "project" / "qa" / "loop-seam"
        qa_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        samples = [(0.0, "loop-1-start")] + [(seam["outputSeconds"] - 0.05, f"loop-{seam['seamIndex']}-end") for seam in seams] \
            + [(seam["outputSeconds"] + 0.05, f"loop-{seam['seamIndex'] + 1}-start") for seam in seams]
        samples.append((duration_ms / 1000 - 0.05, "output-end"))
        for seconds, label in samples:
            output = qa_dir / f"{label}.png"
            extract(still.background, seconds, output,
                    "fps=30,scale=-2:1080,crop='min(iw,1920)':1080,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                    seek_seconds=seconds % video_seconds)
            if Image is not None:
                frames.append(Image.open(output).convert("RGB").resize((640, 360)))
        if Image is not None and frames:
            columns = max(1, args.columns)
            rows = (len(frames) + columns - 1) // columns
            sheet = Image.new("RGB", (640 * columns, 360 * rows), "black")
            for index, frame in enumerate(frames):
                sheet.paste(frame, ((index % columns) * 640, (index // columns) * 360))
            sheet_path = qa_dir / "loop-seam-contact-sheet.png"
            sheet.save(sheet_path)
            contact = str(sheet_path.relative_to(root)).replace("\\", "/")

    report = {
        "schemaVersion": 1,
        "project": root.name,
        "preset": manifest.get("pipelinePreset"),
        "backgroundAsset": manifest.get("backgroundAsset"),
        "backgroundDurationSeconds": round(video_seconds, 3),
        "outputDurationSeconds": round(duration_ms / 1000, 3),
        "loopsInOutput": round(duration_ms / 1000 / video_seconds, 3),
        "transitionKind": scene.get("transitionOut", {}).get("kind", "none"),
        "seams": seams,
        "seamsInsideLyric": sum(1 for seam in seams if seam["insideLyric"]),
        "contactSheet": contact,
        "finding": "Each seam restarts the (muted) background from its first frame. "
                   "The video-loop preset declares no per-iteration crossfade, so a seam inside a "
                   "lyric line is inherent to the requested looping background, not a defect; "
                   "softening it needs a custom renderer.",
    }
    output = args.report or root / "project" / "qa" / "loop-seam-report.json"
    write_json(output, report)
    print(json.dumps({key: report[key] for key in
                      ("backgroundDurationSeconds", "loopsInOutput", "seamsInsideLyric", "transitionKind", "contactSheet")},
                     ensure_ascii=False, indent=2))
    for seam in seams:
        print(f"  seam {seam['seamIndex']} @ {seam['outputSeconds']}s -> {seam['foregroundState']}")


if __name__ == "__main__":
    main()
