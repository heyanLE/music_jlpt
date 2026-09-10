#!/usr/bin/env python3
"""Render the reviewed project with a dialogue-bearing episode intro.

The final output is built from the current frames, never from an older composite:
episode clip -> hard cut to ED video -> background-only fade to Gaussian cover.
Foreground is blank during the episode intro.  From the hard cut onward it uses
the reviewed foreground timeline and transparent Foobar spectrum.  The frozen
hybrid FLAC is stream-copied unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video")
SHARED_RENDERER = SKILL_ROOT / "scripts" / "render_video.py"
TIMELINE_BUILDER = SKILL_ROOT / "scripts" / "build_foreground_timeline.py"
SPECTRUM_RENDERER = SKILL_ROOT / "scripts" / "render_foobar_spectrum.py"
EXPECTED_DEPENDENCY_HASHES = {
    SHARED_RENDERER: "edbbd4eb5e6602b919a547dd115c10d51e61ad0d09cb739a1651ac0a31e9fc8e",
    TIMELINE_BUILDER: "6ac68b7ac62ea813d22118a82035aa5c34d128410d0805c51e2a5c0fc298d2f6",
    SPECTRUM_RENDERER: "a86096b6055426bde5c5be39eccf74d3a3068acfb4d41a0c55cc97e9cc470fa3",
}

EPISODE_SOURCE_START_SECONDS = 1319.0
EPISODE_DURATION_SECONDS = 21.75525
HANDOFF_MS = 21755.25
STAGE1_END_MS = 106851
BACKGROUND_FADE_MS = 500


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=start_time,duration:stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,sample_rate,bits_per_raw_sample,start_time",
            "-of", "json", str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def verify_dependencies() -> None:
    for path, expected in EXPECTED_DEPENDENCY_HASHES.items():
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"shared dependency changed: {path} expected={expected} actual={actual}")


def load_shared_renderer():
    sys.path.insert(0, str(SKILL_ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("study_renderer", SHARED_RENDERER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--run-id", default="episode-intro-corrected-r2")
    parser.add_argument("--canvas", default="16x9")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    verify_dependencies()
    subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "verify_render_gate.py"),
            str(root),
            "--renderer",
            str(Path(__file__).resolve()),
        ],
        check=True,
    )

    manifest = load(project / "input-manifest.json")
    presentation = load(project / "presentation.json")
    scenes = load(project / "scene-timeline.json")["segments"]
    decision = load(project / "review" / "review-decision.json")
    if decision.get("content") != "approved" or decision.get("frameSha256") != sha256(project / "frames.json"):
        raise SystemExit("review decision does not approve the current frames")
    if manifest.get("pipelinePreset") != "custom-episode-intro-then-existing-approved-content":
        raise SystemExit("unexpected custom pipeline preset")
    expected_scene_ids = ["episode-dialogue-intro", "stage1-video", "stage2-cover-gaussian"]
    if [scene["id"] for scene in scenes] != expected_scene_ids:
        raise SystemExit("unexpected scene timeline")
    if int(scenes[0]["endMs"]) != round(HANDOFF_MS) or int(scenes[1]["endMs"]) != STAGE1_END_MS:
        raise SystemExit("scene boundaries no longer match the approved hard-cut plan")

    outputs = manifest["outputs"]
    canvas = next((item for item in outputs if item["name"] == args.canvas), None)
    if canvas is None:
        raise SystemExit(f"unknown canvas {args.canvas}")
    width, height, fps = int(canvas["width"]), int(canvas["height"]), int(canvas["fps"])
    if (width, height, fps) != (1920, 1080, 30):
        raise SystemExit("custom renderer is approved only for 1920x1080 CFR30")

    episode = root / scenes[0]["asset"]
    background = root / scenes[1]["asset"]
    cover = root / scenes[2]["asset"]
    hybrid_audio = root / manifest["music"]["asset"]
    clean_master = root / manifest["music"]["cleanMasterAsset"]
    for path in (episode, background, cover, hybrid_audio, clean_master):
        if not path.is_file():
            raise SystemExit(f"missing render input: {path}")

    audio_probe = probe(hybrid_audio)
    duration_seconds = float(audio_probe["format"]["duration"])
    duration_ms = round(duration_seconds * 1000)
    if duration_ms != 199718:
        raise SystemExit(f"unexpected hybrid audio duration: {duration_ms} ms")
    stage1_seconds = (STAGE1_END_MS - HANDOFF_MS) / 1000
    stage2_seconds = (duration_ms - STAGE1_END_MS) / 1000
    fade_half_seconds = BACKGROUND_FADE_MS / 2000

    run = project / "work" / args.run_id / args.canvas
    foreground_dir = run / "foreground"
    foreground_dir.mkdir(parents=True, exist_ok=True)
    timeline_path = run / "foreground-timeline.json"
    subprocess.run(
        [
            sys.executable, str(TIMELINE_BUILDER), str(root), str(timeline_path),
            "--duration-ms", str(duration_ms),
        ],
        check=True,
    )
    timeline = load(timeline_path)
    shared = load_shared_renderer()
    timeline["segments"] = shared.apply_cover_visibility_overrides(
        timeline["segments"], presentation["foreground"].get("coverVisibilityOverrides")
    )
    if timeline["summary"].get("unmatched"):
        raise SystemExit(f"foreground timing contains unmatched rows: {timeline['summary']}")

    renderer = shared.ForegroundRenderer(root, width, height)
    state_files: dict[tuple, Path] = {}
    concat_lines: list[str] = []
    last_path: Path | None = None
    for segment in timeline["segments"]:
        key = (segment["kind"], segment.get("frameId"), segment.get("activePartIndex"), segment.get("coverVisible", True))
        if key not in state_files:
            path = foreground_dir / f"state-{len(state_files):05}.png"
            renderer.render(
                segment.get("frameId"),
                segment.get("activePartIndex") if segment["kind"] == "active" else None,
                path,
                cover_only=segment["kind"] == "cover",
                cover_visible=segment.get("coverVisible", True),
            )
            state_files[key] = path
        last_path = state_files[key]
        concat_lines.extend([
            f"file '{last_path.as_posix()}'",
            f"duration {(segment['endMs'] - segment['startMs']) / 1000:.6f}",
        ])
    if last_path is None:
        raise SystemExit("foreground timeline is empty")
    concat_lines.append(f"file '{last_path.as_posix()}'")
    concat_path = run / "foreground.concat.txt"
    concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8", newline="\n")

    spectrum_path = run / "foobar-spectrum.mov"
    subprocess.run(
        [
            sys.executable, str(SPECTRUM_RENDERER), str(clean_master), str(project / "palette.json"),
            str(spectrum_path), "--duration-ms", str(duration_ms),
            "--offset-ms", str(int(manifest["alignment"]["offsetMs"])),
        ],
        check=True,
    )

    overlay_template = load(project / "templates" / "overlay.json")["render"]
    overlay_x = round(overlay_template["xPxAt1920x1080"] * width / 1920)
    overlay_y = round(overlay_template["yPxAt1920x1080"] * height / 1080)
    candidate = run / f"{manifest['slug']}--{args.canvas}--{args.run_id}.mkv"
    stage1_fade_start = max(0.0, stage1_seconds - fade_half_seconds)
    filter_graph = (
        f"[0:v:0]fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,trim=duration={EPISODE_DURATION_SECONDS:.6f},setpts=PTS-STARTPTS[intro];"
        f"[1:v:0]fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,trim=duration={stage1_seconds:.6f},setpts=PTS-STARTPTS,"
        f"fade=t=out:st={stage1_fade_start:.6f}:d={fade_half_seconds:.6f}:color=black[stage1];"
        f"[2:v:0]fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
        f"gblur=sigma=30,eq=brightness=-0.25,trim=duration={stage2_seconds:.6f},setpts=PTS-STARTPTS,"
        f"fade=t=in:st=0:d={fade_half_seconds:.6f}:color=black[stage2];"
        "[intro][stage1][stage2]concat=n=3:v=1:a=0[background];"
        "[3:v:0]fps=30,format=rgba,setpts=PTS-STARTPTS[foreground];"
        "[background][foreground]overlay=0:0:format=auto[learning];"
        "[4:v:0]fps=30,format=rgba,setpts=PTS-STARTPTS[spectrum];"
        f"[learning][spectrum]overlay={overlay_x}:{overlay_y}:format=auto:"
        f"enable='gte(t,{HANDOFF_MS / 1000:.6f})',fps=30,format=yuv420p,"
        "tpad=stop_mode=clone:stop_duration=0.050[video]"
    )
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{EPISODE_SOURCE_START_SECONDS:.6f}", "-t", f"{EPISODE_DURATION_SECONDS:.6f}", "-i", str(episode),
        "-t", f"{stage1_seconds:.6f}", "-i", str(background),
        "-loop", "1", "-t", f"{stage2_seconds:.6f}", "-i", str(cover),
        "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-i", str(spectrum_path),
        "-i", str(hybrid_audio),
        "-filter_complex", filter_graph,
        "-map", "[video]", "-map", "5:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr",
        "-c:a", "copy", "-t", f"{duration_seconds:.6f}", str(candidate),
    ]
    subprocess.run(command, check=True)
    report = {
        "schemaVersion": 2,
        "candidate": str(candidate),
        "candidateSha256": sha256(candidate),
        "customRenderer": Path(__file__).resolve().as_posix(),
        "strategy": "full rebuild from current frames with episode intro and hard-cut handoff",
        "activeHashes": {
            "frames": sha256(project / "frames.json"),
            "inputManifest": sha256(project / "input-manifest.json"),
            "presentation": sha256(project / "presentation.json"),
            "sceneTimeline": sha256(project / "scene-timeline.json"),
        },
        "dependencyHashes": {path.name: sha256(path) for path in EXPECTED_DEPENDENCY_HASHES},
        "foregroundTimeline": timeline["summary"],
        "foregroundStateCount": len(state_files),
        "episodeSourceStartMs": 1319000,
        "outputHandoffMs": HANDOFF_MS,
        "backgroundTransition": "hard cut at episode handoff; 500 ms background-only black fade at Gaussian handoff",
        "spectrum": "transparent Foobar bars, hidden before hard cut, persistent afterward",
        "audioCodecPolicy": "stream-copy frozen hybrid FLAC",
        "probe": probe(candidate),
    }
    write_json(run / "render-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
