#!/usr/bin/env python3
"""Compile reviewed frames and QRC units into an unambiguous foreground timeline."""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from foreground_options import countdown_plan, resolve_options


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def norm(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def mode_at(scenes: list[dict], timestamp: int, default: str) -> str:
    for scene in scenes:
        end = scene["endMs"]
        if scene["startMs"] <= timestamp and (end == "audio-end" or timestamp < end):
            return scene.get("foregroundMode", default)
    return default


def idle_foreground_at(scenes: list[dict], timestamp: int) -> str | None:
    """Return an explicit pre-lyric foreground state for the active scene."""
    for scene in scenes:
        end = scene["endMs"]
        if scene["startMs"] <= timestamp and (end == "audio-end" or timestamp < end):
            return scene.get("idleForeground")
    return None


def match_frame(frame: dict, rows: list[dict]) -> tuple[list[dict], str]:
    target = norm(frame["caption"]["japanese"])
    candidates = [i for i, row in enumerate(rows) if row["startMs"] == frame["startMs"]]
    if not candidates:
        candidates = sorted(range(len(rows)), key=lambda i: abs(rows[i]["startMs"] - frame["startMs"]))[:1]
    for index in candidates:
        if norm(rows[index]["text"]) == target and not rows[index].get("parts"):
            return [rows[index]], "lineFallback"
        combined = ""
        selected = []
        for row in rows[index:index + 4]:
            combined += row["text"]
            selected.append(row)
            if norm(combined) == target:
                return selected, "full" if len(selected) == 1 else "adjacentRows"
            if len(norm(combined)) > len(target):
                break
    return [], "unmatched"


def state_key(state: dict) -> tuple:
    return state["kind"], state.get("frameId"), state.get("activePartIndex"), state.get("countdownValue")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration-ms", type=int, required=True)
    args = parser.parse_args()
    if args.duration_ms <= 0:
        raise SystemExit("--duration-ms must be positive")

    project = args.project_root / "project"
    frames = sorted(load(project / "frames.json")["frames"], key=lambda item: item["startMs"])
    timing_path = project / "timing" / "qm.json"
    if not timing_path.is_file(): timing_path = project / "timing" / "lrc.json"
    rows = load(timing_path)["lines"]
    scenes = load(project / "scene-timeline.json")["segments"]
    presentation = load(project / "presentation.json")["foreground"]
    options = resolve_options(presentation)
    manifest = load(project / "input-manifest.json")
    offset = int(manifest.get("alignment", {}).get("offsetMs", 0))
    default_mode = presentation.get("defaultMode", "persistent" if presentation.get("visibleDuringNoLyric") else "follow-lyrics")
    timing = presentation.get("displayTiming", {})
    tail = int(timing.get("tailProtectionMs", timing.get("postRollMs", 500)))
    if tail != 500:
        raise SystemExit("The fixed follow-lyrics tail protection is 500 ms")
    if timing.get("internalGap", "hold-current-line") != "hold-current-line":
        raise SystemExit("Only internalGap=hold-current-line is supported")

    lines, matches = [], []
    for frame in frames:
        matched, match_mode = match_frame(frame, rows)
        matches.append({"frameId": frame["id"], "mode": match_mode, "qrcRows": len(matched)})
        # Spoken MV prelude captions may live on the final output clock while
        # song lyrics retain the signed music/QRC alignment offset.
        frame_offset = 0 if frame.get("clock") == "output" else offset
        if not matched:
            start, end, parts = frame["startMs"] + frame_offset, frame["endMs"] + frame_offset, []
        else:
            parts = [part for row in matched for part in row.get("parts", [])]
            start = min(row["startMs"] for row in matched) + frame_offset
            end = max(row["endMs"] for row in matched) + frame_offset
            if not parts:
                parts = [{"text": frame["caption"]["japanese"], "startMs": start - frame_offset, "endMs": end - frame_offset}]
        normalized_parts = []
        for index, part in enumerate(parts):
            part_start = int(part["startMs"]) + frame_offset
            part_end = int(part.get("endMs", part["startMs"] + part.get("durationMs", 0))) + frame_offset
            normalized_parts.append({"index": index, "text": part["text"], "startMs": part_start, "endMs": part_end})
        lines.append({"frameId": frame["id"], "text": frame["caption"]["japanese"], "startMs": start, "endMs": end, "parts": normalized_parts, "matchMode": match_mode})

    lines.sort(key=lambda line: line["startMs"])
    countdown = countdown_plan(lines, options["countdown"]["enabled"], args.duration_ms)
    boundaries = {0, args.duration_ms}
    for item in countdown["segments"]: boundaries.update((item["startMs"], item["endMs"]))
    for scene in scenes:
        boundaries.add(max(0, int(scene["startMs"])))
        if isinstance(scene["endMs"], int): boundaries.add(min(args.duration_ms, scene["endMs"]))
    for line in lines:
        boundaries.update((max(0, line["startMs"]), min(args.duration_ms, line["endMs"]), min(args.duration_ms, line["endMs"] + tail)))
        for part in line["parts"]:
            boundaries.update((max(0, part["startMs"]), min(args.duration_ms, part["endMs"])))
    points = sorted(value for value in boundaries if 0 <= value <= args.duration_ms)

    segments: list[dict] = []
    for start, end in zip(points, points[1:]):
        if end <= start: continue
        mid = (start + end) // 2
        current = next((line for line in reversed(lines) if line["startMs"] <= mid < line["endMs"]), None)
        if current:
            active = next((part for part in current["parts"] if part["startMs"] <= mid < part["endMs"]), None)
            state = {"kind": "active" if active else "neutral", "frameId": current["frameId"]}
            if active: state["activePartIndex"] = active["index"]
        else:
            previous = next((line for line in reversed(lines) if line["startMs"] <= mid), None)
            if not previous:
                # A prelude may deliberately show only the cover.  This is not a
                # learning frame: it has no veil, lyrics, translation, or cards.
                first = next((line for line in lines if line["text"].strip()), None)
                if options["preludeMode"] == "first-line" and first:
                    state = {"kind": "neutral", "frameId": first["frameId"]}
                else:
                    state = {"kind": "cover"} if idle_foreground_at(scenes, mid) == "cover" else {"kind": "blank"}
            elif mode_at(scenes, mid, default_mode) == "persistent":
                state = {"kind": "neutral", "frameId": previous["frameId"]}
            else:
                next_line = next((line for line in lines if line["startMs"] > previous["startMs"]), None)
                protected_end = min(previous["endMs"] + tail, next_line["startMs"] if next_line else args.duration_ms)
                state = {"kind": "neutral", "frameId": previous["frameId"]} if mid < protected_end else {"kind": "blank"}
        count = next((item["value"] for item in countdown["segments"] if item["startMs"] <= mid < item["endMs"]), None)
        if count is not None: state["countdownValue"] = count
        segment = {"startMs": start, "endMs": end, **state}
        if segments and segments[-1]["endMs"] == start and state_key(segments[-1]) == state_key(segment):
            segments[-1]["endMs"] = end
        else:
            segments.append(segment)

    summary = {
        "full": sum(item["mode"] == "full" for item in matches),
        "adjacentRows": sum(item["mode"] == "adjacentRows" for item in matches),
        "lineFallback": sum(item["mode"] == "lineFallback" for item in matches),
        "unmatched": sum(item["mode"] == "unmatched" for item in matches),
        "blankSegments": sum(item["kind"] == "blank" for item in segments),
        "neutralSegments": sum(item["kind"] == "neutral" for item in segments),
        "activeSegments": sum(item["kind"] == "active" for item in segments),
    }
    write(args.output, {"schemaVersion": 2, "clock": "output", "durationMs": args.duration_ms, "offsetMs": offset, "learningAids": options, "countdown": countdown, "segments": segments, "matches": matches, "summary": summary})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
