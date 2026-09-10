#!/usr/bin/env python3
"""Render the approved three-video sequential timeline for kanjou-glass."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SKILL_SCRIPTS = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts")
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


def background_inputs_and_filter(
    root: Path,
    scenes: list[dict],
    width: int,
    height: int,
    duration_ms: int,
) -> tuple[list[str], str, int]:
    args: list[str] = []
    chains: list[str] = []
    for index, scene in enumerate(scenes):
        if scene.get("mode") != "video-clip":
            raise RuntimeError(f"Unsupported custom scene mode: {scene.get('mode')}")
        if scene.get("sourceAudio") != "mute":
            raise RuntimeError(f"Background source audio must be muted: {scene.get('id')}")
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
        if fade_in.get("kind") not in (None, "none") or fade_out.get("kind") not in (None, "none"):
            raise RuntimeError("This approved timeline requires hard cuts without transitions")
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
    music_probe = probe(music)
    music_duration_ms = round(float(music_probe["format"]["duration"]) * 1000)
    offset = int(manifest.get("alignment", {}).get("offsetMs", 0))
    duration_ms = max(1, music_duration_ms + offset)
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
        "audioCodecPolicy": "FLAC stream-copy",
        "foregroundTimeline": timeline["summary"],
    })
    print(json.dumps({
        "candidate": str(candidate),
        "durationMs": duration_ms,
        "states": len(state_files),
        "spectrum": overlay_on,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
