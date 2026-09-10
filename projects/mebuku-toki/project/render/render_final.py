#!/usr/bin/env python3
"""Render the approved dual-video custom timeline for mebuku-toki."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SKILL_SCRIPTS = Path("C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))

from render_video import (  # noqa: E402
    ForegroundRenderer,
    apply_cover_visibility_overrides,
    load,
    probe,
    sha,
    write,
)
from verify_render_gate import verify_render_gate  # noqa: E402


def apply_lyric_clock_correction(timeline: dict, correction_ms: int, duration_ms: int) -> dict:
    """Translate the normalized foreground state sequence on the output clock."""
    if not correction_ms:
        timeline["lyricSourceClockCorrectionMs"] = 0
        timeline["lyricOutputOffsetMs"] = int(timeline.get("offsetMs", 0))
        return timeline

    shifted: list[dict] = []
    for segment in timeline["segments"]:
        start = max(0, int(segment["startMs"]) + correction_ms)
        end = min(duration_ms, int(segment["endMs"]) + correction_ms)
        if end <= start:
            continue
        candidate = {**segment, "startMs": start, "endMs": end}
        key = (candidate["kind"], candidate.get("frameId"), candidate.get("activePartIndex"))
        if shifted:
            previous = shifted[-1]
            previous_key = (previous["kind"], previous.get("frameId"), previous.get("activePartIndex"))
            if previous["endMs"] == start and previous_key == key:
                previous["endMs"] = end
                continue
        shifted.append(candidate)

    if not shifted or shifted[0]["startMs"] > 0:
        shifted.insert(0, {"startMs": 0, "endMs": shifted[0]["startMs"] if shifted else duration_ms, "kind": "blank"})
    if shifted[-1]["endMs"] < duration_ms:
        if shifted[-1]["kind"] == "blank":
            shifted[-1]["endMs"] = duration_ms
        else:
            shifted.append({"startMs": shifted[-1]["endMs"], "endMs": duration_ms, "kind": "blank"})

    for previous, current in zip(shifted, shifted[1:]):
        if previous["endMs"] != current["startMs"]:
            raise RuntimeError("Corrected foreground timeline is not contiguous")
    timeline["segments"] = shifted
    timeline["musicOffsetMs"] = int(timeline.get("offsetMs", 0))
    timeline["lyricSourceClockCorrectionMs"] = correction_ms
    timeline["lyricOutputOffsetMs"] = timeline["musicOffsetMs"] + correction_ms
    return timeline


def background_inputs_and_filter(
    root: Path,
    scenes: list[dict],
    width: int,
    height: int,
    duration_ms: int,
) -> tuple[list[str], str, int]:
    """Build source-trimmed, aspect-preserving background segments."""
    args: list[str] = []
    chains: list[str] = []
    for index, scene in enumerate(scenes):
        if scene.get("mode") != "video-clip":
            raise RuntimeError(f"Unsupported custom scene mode: {scene.get('mode')}")
        args += ["-i", str(root / scene["asset"])]
        output_end = duration_ms if scene["endMs"] == "audio-end" else int(scene["endMs"])
        segment_duration = (output_end - int(scene["startMs"])) / 1000
        source_start = int(scene.get("sourceStartMs", 0)) / 1000
        if segment_duration <= 0:
            raise RuntimeError(f"Invalid scene duration: {scene['id']}")
        chain = (
            f"[{index}:v]fps=30,"
            f"scale=-2:{height},"
            f"crop='min(iw,{width})':{height},"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih):black,"
            f"trim=start={source_start:.6f}:duration={segment_duration:.6f},"
            "setpts=PTS-STARTPTS"
        )
        fade_in = scene.get("transitionIn", {})
        fade_out = scene.get("transitionOut", {})
        if fade_in.get("kind") in ("black-fade", "white-fade") and fade_in.get("durationMs", 0):
            color = "white" if fade_in["kind"] == "white-fade" else "black"
            chain += f",fade=t=in:st=0:d={fade_in['durationMs']/2000:.6f}:color={color}"
        if fade_out.get("kind") in ("black-fade", "white-fade") and fade_out.get("durationMs", 0):
            color = "white" if fade_out["kind"] == "white-fade" else "black"
            half = fade_out["durationMs"] / 2000
            chain += f",fade=t=out:st={max(0, segment_duration-half):.6f}:d={half:.6f}:color={color}"
        chains.append(f"{chain}[bg{index}]")
    labels = "".join(f"[bg{index}]" for index in range(len(scenes)))
    chains.append(f"{labels}concat=n={len(scenes)}:v=1:a=0[background]")
    return args, ";".join(chains), len(scenes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--canvas", default="16x9")
    parser.add_argument("--output-name")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    verify_render_gate(root, Path(__file__).resolve())
    manifest = load(project / "input-manifest.json")
    presentation = load(project / "presentation.json")
    scenes = load(project / "scene-timeline.json")["segments"]
    outputs = manifest.get("outputs", [])
    canvas = next((item for item in outputs if item.get("name") == args.canvas), None)
    if canvas is None:
        raise SystemExit(f"Unknown canvas: {args.canvas}")
    width, height, fps = int(canvas["width"]), int(canvas["height"]), int(canvas.get("fps", 30))
    if fps != 30:
        raise SystemExit("This renderer requires CFR 30 fps")

    music = root / manifest["music"]["asset"]
    music_duration = round(float(probe(music)["format"]["duration"]) * 1000)
    offset = int(manifest.get("alignment", {}).get("offsetMs", 0))
    duration_ms = max(1, music_duration + offset)
    run = project / "work" / args.run_id / args.canvas
    foreground_dir = run / "foreground"
    foreground_dir.mkdir(parents=True, exist_ok=True)

    timeline_path = run / "foreground-timeline.json"
    subprocess.run([
        sys.executable,
        str(SKILL_SCRIPTS / "build_foreground_timeline.py"),
        str(root),
        str(timeline_path),
        "--duration-ms",
        str(duration_ms),
    ], check=True)
    timeline = load(timeline_path)
    lyric_correction = int(manifest.get("lyrics", {}).get("clockNormalization", {}).get("correctionMs", 0))
    timeline = apply_lyric_clock_correction(timeline, lyric_correction, duration_ms)
    timeline["segments"] = apply_cover_visibility_overrides(
        timeline["segments"],
        presentation["foreground"].get("coverVisibilityOverrides"),
    )
    write(timeline_path, timeline)

    renderer = ForegroundRenderer(root, width, height)
    state_files: dict[tuple, Path] = {}
    concat_lines: list[str] = []
    last_path: Path | None = None
    for segment in timeline["segments"]:
        key = (
            segment["kind"],
            segment.get("frameId"),
            segment.get("activePartIndex"),
            segment["coverVisible"],
        )
        if key not in state_files:
            state_path = foreground_dir / f"state-{len(state_files):05}.png"
            renderer.render(
                segment.get("frameId"),
                segment.get("activePartIndex") if segment["kind"] == "active" else None,
                state_path,
                cover_only=segment["kind"] == "cover",
                cover_visible=segment["coverVisible"],
            )
            state_files[key] = state_path
        last_path = state_files[key]
        concat_lines += [
            f"file '{last_path.as_posix()}'",
            f"duration {(segment['endMs'] - segment['startMs']) / 1000:.6f}",
        ]
    if last_path is None:
        raise RuntimeError("Foreground timeline contains no states")
    concat_lines.append(f"file '{last_path.as_posix()}'")
    concat_path = run / "foreground.concat.txt"
    concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8", newline="\n")

    background_args, background_filter, background_count = background_inputs_and_filter(
        root, scenes, width, height, duration_ms
    )
    command = ["ffmpeg", "-y", "-v", "error", *background_args, "-f", "concat", "-safe", "0", "-i", str(concat_path)]
    foreground_index = background_count
    overlay = presentation.get("floatingOverlay", {})
    overlay_on = bool(overlay.get("enabled"))
    spectrum_path = run / "foobar-spectrum.mov"
    if overlay_on:
        subprocess.run([
            sys.executable,
            str(SKILL_SCRIPTS / "render_foobar_spectrum.py"),
            str(music),
            str(project / "palette.json"),
            str(spectrum_path),
            "--duration-ms",
            str(duration_ms),
            "--offset-ms",
            str(offset),
        ], check=True)
        command += ["-i", str(spectrum_path)]
        spectrum_index = foreground_index + 1
    if offset >= 0:
        command += ["-itsoffset", f"{offset / 1000:.6f}", "-i", str(music)]
    else:
        command += ["-ss", f"{-offset / 1000:.6f}", "-i", str(music)]
    music_index = foreground_index + 1 + int(overlay_on)

    filters = [
        background_filter,
        f"[{foreground_index}:v]fps=30,format=rgba,setpts=PTS-STARTPTS[foreground]",
        "[background][foreground]overlay=0:0:format=auto[learning]",
    ]
    if overlay_on:
        overlay_template = load(project / "templates" / "overlay.json")["render"]
        x = round(overlay_template["xPxAt1920x1080"] * width / 1920)
        y = round(overlay_template["yPxAt1920x1080"] * height / 1080)
        filters += [
            f"[{spectrum_index}:v]fps=30,format=rgba,setpts=PTS-STARTPTS[spectrum]",
            f"[learning][spectrum]overlay={x}:{y}:format=auto,fps=30,format=yuv420p[video]",
        ]
    else:
        filters += ["[learning]fps=30,format=yuv420p[video]"]

    filename = args.output_name or f"{manifest['slug']}--{args.canvas}--{args.run_id}.mkv"
    candidate = run / filename
    command += [
        "-filter_complex", ";".join(filters),
        "-map", "[video]",
        "-map", f"{music_index}:a:0",
        "-t", f"{duration_ms / 1000:.6f}",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-fps_mode", "cfr",
        "-c:a", "copy",
        str(candidate),
    ]
    subprocess.run(command, check=True)
    write(run / "render-report.json", {
        "schemaVersion": 2,
        "candidate": str(candidate),
        "candidateSha256": sha(candidate),
        "activeHashes": {
            "inputManifest": sha(project / "input-manifest.json"),
            "presentation": sha(project / "presentation.json"),
            "sceneTimeline": sha(project / "scene-timeline.json"),
            "frames": sha(project / "frames.json"),
        },
        "renderer": str(Path(__file__).resolve()),
        "layers": ["background", "foreground", "floatingOverlay" if overlay_on else "floatingOverlay-disabled"],
        "scenes": scenes,
        "foregroundDefaultMode": presentation["foreground"]["defaultMode"],
        "durationMs": duration_ms,
        "offsetMs": offset,
        "lyricsClockCorrectionMs": lyric_correction,
        "lyricOutputOffsetMs": offset + lyric_correction,
        "audioCodecPolicy": "stream-copy",
        "foregroundTimeline": timeline["summary"],
    })
    print(json.dumps({
        "candidate": str(candidate),
        "durationMs": duration_ms,
        "states": len(state_files),
        "spectrum": overlay_on,
        "lyricsClockCorrectionMs": lyric_correction,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
