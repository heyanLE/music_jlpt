#!/usr/bin/env python3
"""Assert the compiled foreground timeline against the learning-aid contract.

Objective checks only - contiguity, full coverage, countdown placement, prelude
mode, follow-lyrics gap/tail behaviour, neighbour availability and state
completeness. Nothing here inspects pixels; it proves the timeline the renderer
will follow, which is what every preview and QA sample depends on.

Usage
    python check_timeline_invariants.py PROJECT_ROOT TIMELINE_JSON [--duration-ms N] [--out REPORT]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def project_duration_ms(root: Path) -> int:
    """Music duration plus the signed alignment offset, exactly as the renderer computes it."""
    manifest = load(root / "project" / "input-manifest.json")
    music = root / manifest["music"]["asset"]
    seconds = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(music)],
        check=True, text=True, capture_output=True,
    ).stdout.strip())
    return round(seconds * 1000) + int(manifest.get("alignment", {}).get("offsetMs", 0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    duration_ms = args.duration_ms or project_duration_ms(root)
    timeline = load(args.timeline)
    frames = load(project / "frames.json")["frames"]
    presentation = load(project / "presentation.json")["foreground"]
    # Segments live on the output clock; frames.json times are on the music clock. With a
    # non-zero alignment offset the two differ, so every comparison has to shift first.
    offset_ms = int(load(project / "input-manifest.json").get("alignment", {}).get("offsetMs", 0))
    for frame in frames:
        frame["outputStartMs"] = frame["startMs"] + offset_ms
        frame["outputEndMs"] = frame["endMs"] + offset_ms
    segments = timeline["segments"]
    settings = timeline.get("learningAids", {})
    problems: list[str] = []
    findings: dict = {}

    # 1. Contiguity: the foreground must never have a hole or an overlap.
    if segments[0]["startMs"] != 0:
        problems.append(f"timeline starts at {segments[0]['startMs']} ms, expected 0")
    if segments[-1]["endMs"] != duration_ms:
        problems.append(f"timeline ends at {segments[-1]['endMs']} ms, expected {duration_ms}")
    for previous, current in zip(segments, segments[1:]):
        if previous["endMs"] != current["startMs"]:
            problems.append(f"gap/overlap between {previous['endMs']} and {current['startMs']}")
    findings["segments"] = len(segments)

    # 2. Countdown 3/2/1, one second each, ending exactly at the first highlighted state.
    countdown = timeline.get("countdown", {})
    values = [item["value"] for item in countdown.get("segments", [])]
    findings["countdown"] = countdown
    if settings.get("countdown", {}).get("enabled", presentation.get("countdown", {}).get("enabled")):
        if values != [3, 2, 1]:
            problems.append(f"countdown values are {values}, expected [3, 2, 1]")
        for item in countdown.get("segments", []):
            if item["endMs"] - item["startMs"] != 1000:
                problems.append(f"countdown {item['value']} lasts {item['endMs'] - item['startMs']} ms, expected 1000")
        onset = countdown.get("onsetMs")
        first_active = next((segment for segment in segments if segment["kind"] == "active"), None)
        if onset is None or first_active is None or first_active["startMs"] != onset:
            problems.append(f"countdown onset {onset} does not coincide with the first highlighted state "
                            f"{first_active['startMs'] if first_active else None}")
        timeline_values = sorted({segment.get("countdownValue") for segment in segments if segment.get("countdownValue")})
        findings["countdownValuesInTimeline"] = timeline_values
        if timeline_values != [1, 2, 3]:
            problems.append(f"timeline countdown values {timeline_values}, expected [1, 2, 3]")

    # 3. Prelude honours the configured mode.
    onset = countdown.get("onsetMs") or 0
    prelude = [segment for segment in segments if segment["endMs"] <= onset]
    ordered = [frame["id"] for frame in sorted(frames, key=lambda item: item["startMs"])]
    findings["prelude"] = {
        "mode": presentation.get("preludeMode"),
        "segments": len(prelude),
        "kinds": sorted({segment["kind"] for segment in prelude}),
        "frameIds": sorted({segment.get("frameId") for segment in prelude if segment.get("frameId")}),
    }
    if presentation.get("preludeMode") == "first-line" and ordered:
        if {segment["kind"] for segment in prelude} - {"neutral"}:
            problems.append("prelude contains a highlighted or blank state under preludeMode=first-line")
        if {segment.get("frameId") for segment in prelude if segment.get("frameId")} != {ordered[0]}:
            problems.append("prelude does not show the first study frame")
    if presentation.get("preludeMode") == "countdown-reveal" and ordered:
        # Nothing before the countdown, then the complete first study frame beside 3/2/1.
        countdown_start = min((item["startMs"] for item in countdown.get("segments", [])), default=None)
        before = [segment for segment in segments if countdown_start is not None and segment["endMs"] <= countdown_start]
        if any(segment["kind"] not in ("blank", "cover") for segment in before):
            problems.append("countdown-reveal shows foreground content before the countdown starts")
        if countdown_start is not None and ordered:
            during = [segment for segment in segments if segment["startMs"] >= countdown_start and segment["endMs"] <= onset]
            if {segment.get("frameId") for segment in during if segment.get("frameId")} != {ordered[0]}:
                problems.append("countdown-reveal does not show the first study frame during the countdown")
            if any(segment["kind"] != "neutral" for segment in during):
                problems.append("countdown-reveal highlights content during the countdown")

    # 4. Follow-lyrics protection: hold at most tailProtectionMs after a line, then hide.
    # A persistent scene (e.g. the Gaussian stage of the hybrid preset) legitimately keeps
    # the last line on screen, so these rules apply only where the scene says follow-lyrics.
    scenes = load(project / "scene-timeline.json")["segments"]

    def scene_mode_at(timestamp: int) -> str:
        for scene in scenes:
            end = scene["endMs"]
            if scene["startMs"] <= timestamp and (end == "audio-end" or timestamp < end):
                return scene.get("foregroundMode", presentation.get("defaultMode", "follow-lyrics"))
        return presentation.get("defaultMode", "follow-lyrics")

    tail = int(presentation.get("displayTiming", {}).get("tailProtectionMs", 500))
    for segment in segments:
        if segment["kind"] != "neutral" or not segment.get("frameId") or segment.get("countdownValue"):
            continue
        if scene_mode_at(segment["startMs"]) != "follow-lyrics":
            continue
        frame = next((item for item in frames if item["id"] == segment["frameId"]), None)
        if frame and segment["startMs"] >= frame["outputEndMs"] and segment["endMs"] - frame["outputEndMs"] > tail:
            problems.append(f"{frame['id']} holds {segment['endMs'] - frame['outputEndMs']} ms past the line (> {tail} ms)")
    findings["sceneModes"] = sorted({scene.get("foregroundMode") for scene in scenes})
    if ordered:
        last = max(frames, key=lambda item: item["endMs"])
        after_last = [segment for segment in segments if segment["startMs"] >= last["outputEndMs"]]
        findings["afterLastLine"] = {
            "frameId": last["id"], "lineEndMs": last["outputEndMs"],
            "finalSceneMode": scene_mode_at(max(0, duration_ms - 1)),
            "states": [{"kind": segment["kind"], "startMs": segment["startMs"], "endMs": segment["endMs"]} for segment in after_last],
        }
        if scene_mode_at(max(0, duration_ms - 1)) == "follow-lyrics" and (not after_last or after_last[-1]["kind"] != "blank"):
            problems.append("output does not end hidden after the final line in a follow-lyrics scene")

    # 5. Every row is displayed and can highlight; state count feeds the render estimate.
    displayed = {segment.get("frameId") for segment in segments if segment.get("frameId")}
    missing = [frame["id"] for frame in frames if frame["id"] not in displayed]
    if missing:
        problems.append(f"frames never displayed: {missing}")
    findings["framesWithoutHighlight"] = [
        frame["id"] for frame in frames
        if frame["id"] not in {segment.get("frameId") for segment in segments if segment["kind"] == "active"}
    ]
    findings["neighbourBoundaries"] = {"first": ordered[0] if ordered else None, "last": ordered[-1] if ordered else None,
                                       "orderedCount": len(ordered)}
    findings["blankSegments"] = [{"startMs": segment["startMs"], "endMs": segment["endMs"]}
                                 for segment in segments if segment["kind"] == "blank"]
    findings["uniqueStates"] = len({(segment["kind"], segment.get("frameId"), segment.get("activePartIndex"),
                                     segment.get("countdownValue")) for segment in segments})

    report = {
        "schemaVersion": 1,
        "project": root.name,
        "durationMs": duration_ms,
        "timeline": str(args.timeline).replace("\\", "/"),
        "result": "passed" if not problems else "failed",
        "problems": problems,
        "findings": findings,
    }
    output = args.out or project / "qa" / "timeline-invariants.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
