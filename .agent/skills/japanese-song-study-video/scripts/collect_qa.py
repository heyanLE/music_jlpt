#!/usr/bin/env python3
"""Collect deterministic probe data and representative QA screenshots.

The report remains pending until an agent visually inspects the images and marks it passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def contact_sheet(root: Path, qa_dir: Path, screenshots: list[dict], columns: int = 4, tile_width: int = 480) -> str | None:
    """Compose every sample into one labelled grid.

    Reading fifteen separate images costs far more attention than reading one grid,
    so the sheet is the primary artifact and the individual frames are the fallback
    for anything that looks wrong on it.
    """
    if not screenshots:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
        from runtime_font import font_path
    except ImportError:
        return None
    tiles = []
    for entry in screenshots:
        path = Path(entry["path"])
        if not path.is_absolute():
            path = root / path
        with Image.open(path) as image:
            height = round(tile_width * image.height / image.width)
            tiles.append((entry["name"], entry["timestampMs"], image.convert("RGB").resize((tile_width, height))))
    if not tiles:
        return None
    tile_height = tiles[0][2].height
    label_height = 22
    columns = max(1, min(columns, len(tiles)))
    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (tile_width * columns, (tile_height + label_height) * rows), "#101216")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(font_path(), 14)
    for index, (name, timestamp_ms, tile) in enumerate(tiles):
        x, y = (index % columns) * tile_width, (index // columns) * (tile_height + label_height)
        sheet.paste(tile, (x, y + label_height))
        draw.text((x + 4, y + 3), f"{name}  {timestamp_ms} ms", font=font, fill="#e8e8e8")
    output = qa_dir / "contact-sheet.png"
    sheet.save(output)
    return output.name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("qa_dir", type=Path)
    parser.add_argument("--contact-columns", type=int, default=4)
    parser.add_argument("--contact-width", type=int, default=480, help="Width of one contact-sheet tile")
    parser.add_argument("--no-contact-sheet", action="store_true")
    args = parser.parse_args()
    root = args.project_root.resolve(); project = root / "project"
    args.candidate = args.candidate.resolve()
    args.qa_dir = args.qa_dir.resolve()
    args.qa_dir.mkdir(parents=True, exist_ok=True)
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,bits_per_raw_sample", "-of", "json", str(args.candidate)], check=True, text=True, capture_output=True).stdout)
    render_report_path = args.candidate.parent / "render-report.json"
    render_report = load(render_report_path) if render_report_path.is_file() else {}
    if render_report.get("candidateSha256") and render_report["candidateSha256"] != hashlib.sha256(args.candidate.read_bytes()).hexdigest():
        raise SystemExit("Render report does not hash this candidate")
    frames = load(project / "frames.json")["frames"]
    offset = int(load(project / "input-manifest.json").get("alignment", {}).get("offsetMs", 0))
    timeline_candidates = sorted((args.candidate.parent).glob("foreground-timeline.json"))
    timeline = load(timeline_candidates[0]) if timeline_candidates else None
    samples: dict[str, int] = {}
    if frames:
        samples["first-lyric"] = frames[0]["startMs"] + 100
        samples["last-lyric"] = frames[-1]["startMs"] + 100
        samples["maximum-cards"] = max(frames, key=lambda item: len(item.get("grammarCards", [])))["startMs"] + 100
        pure = next((item for item in frames if item["caption"]["japanese"].isascii()), None)
        mixed = next((item for item in frames if any(ch.isascii() and ch.isalpha() for ch in item["caption"]["japanese"]) and not item["caption"]["japanese"].isascii()), None)
        loan = next((item for item in frames if any(card.get("sourceWord") for card in item.get("grammarCards", []))), None)
        if pure: samples["pure-english"] = pure["startMs"] + 100
        if mixed: samples["mixed-language"] = mixed["startMs"] + 100
        if loan: samples["loanword"] = loan["startMs"] + 100
        # Frame timestamps are music clock unless explicitly marked output.
        for name, timestamp in list(samples.items()):
            frame = next((item for item in frames if item["startMs"] + 100 == timestamp), None)
            if frame and frame.get("clock") != "output": samples[name] = timestamp + offset
    scenes = render_report.get("scenes") or load(project / "scene-timeline.json")["segments"]
    for scene in scenes[1:]: samples[f"transition-{scene['id']}"] = int(scene["startMs"]) + 100
    if timeline:
        samples["prelude"] = 0
        for item in timeline.get("countdown", {}).get("segments", []):
            samples[f"countdown-{item['value']}"] = (item["startMs"] + item["endMs"]) // 2
        onset = timeline.get("countdown", {}).get("onsetMs")
        if onset is not None: samples["countdown-end"] = max(0, onset + 50)
        if timeline.get("learningAids", {}).get("neighbors", {}).get("enabled") and len(frames) > 2:
            # A neighbour switch is where two consecutive active states name different
            # frames. Sampling "the middle frame" instead frequently lands in a blank
            # gap, which proves nothing about the switch.
            segments = timeline["segments"]
            # The displayed line usually changes through a neutral/blank state, so a
            # switch is "the first state naming a different frame than the previous
            # displayed one", not an active-to-active adjacency.
            switches, previous_frame = [], None
            for segment in segments:
                frame_id = segment.get("frameId")
                if frame_id and previous_frame and frame_id != previous_frame:
                    switches.append(segment["startMs"])
                if frame_id:
                    previous_frame = frame_id
            if switches:
                samples["neighbors-before-switch"] = max(0, switches[0] - 50)
                samples["neighbors-after-switch"] = switches[0] + 50
            middle_active = next(
                (segment for index, segment in enumerate(segments)
                 if segment["kind"] == "active" and 0 < index < len(segments) - 1), None
            )
            if middle_active:
                samples["neighbors-middle-line"] = (middle_active["startMs"] + middle_active["endMs"]) // 2
        blank = next((item for item in timeline["segments"] if item["kind"] == "blank" and item["startMs"] > 0), None)
        retained = next((item for item in timeline["segments"] if item["kind"] == "neutral" and item["endMs"] - item["startMs"] >= 500), None)
        if blank: samples["follow-gap"] = blank["startMs"] + min(100, (blank["endMs"] - blank["startMs"]) // 2)
        if retained: samples["line-hold"] = retained["startMs"] + min(100, (retained["endMs"] - retained["startMs"]) // 2)
    duration_ms = round(float(probe["format"]["duration"]) * 1000)
    samples["output-tail"] = max(0, duration_ms - 100)
    screenshots=[]
    for name, timestamp in samples.items():
        timestamp = max(0, min(duration_ms - 1, timestamp)); output = args.qa_dir / f"{name}.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp/1000:.3f}", "-i", str(args.candidate), "-frames:v", "1", str(output)], check=True)
        screenshots.append({"name": name, "timestampMs": timestamp, "path": output.relative_to(root).as_posix()})
    report = {"schemaVersion": 2, "result": "pending-visual-review", "candidate": args.candidate.relative_to(root).as_posix(), "candidateSha256": hashlib.sha256(args.candidate.read_bytes()).hexdigest(), "renderReport": render_report_path.relative_to(root).as_posix() if render_report_path.is_file() else None, "probe": probe, "screenshots": screenshots, "requiredVisualChecks": ["three-layer order", "background fit and transitions", "foreground gap mode", "annotation anchors", "English timing", "one-row cards and two-line meaning", "transparent persistent spectrum", "final line"]}
    report["requiredVisualChecks"] += ["preludeMode matches configuration", "static neighbors share lyric/annotation/romaji baseline and clip only at canvas edges", "countdown changes 3/2/1 before onset and vanishes at onset without shifting audio"]
    contact = None if args.no_contact_sheet else contact_sheet(root, args.qa_dir, screenshots, columns=args.contact_columns, tile_width=args.contact_width)
    if contact:
        report["contactSheet"] = contact
        report["contactSheetNote"] = ("One labelled image carrying every sample: inspect this first and open an "
                                      "individual frame only where something looks wrong.")
    output = args.qa_dir / "qa-report.json"; output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(output), "screenshots": len(screenshots), "contactSheet": contact, "result": report["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
