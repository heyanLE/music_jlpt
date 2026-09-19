#!/usr/bin/env python3
"""Pre-flight the renderer against the frozen content, before an authorized run.

Two independent checks, both cheap compared with discovering the problem 3 minutes
into a real encode:

* layer check - paint every unique foreground state to a scratch directory, which
  surfaces any card that cannot be laid out (overflow, bad ruby anchor, missing field);
* graph check - build the real background filter chain and encode a short probe with
  the spectrum overlay and codec-copied audio, then probe the result.

No candidate is produced and the render gate is not exercised.

Usage
    python preflight_render.py PROJECT_ROOT [--run-id ID] [--probe-seconds 2] [--out REPORT]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from foreground_options import resolve_options  # noqa: E402
from render_video import ForegroundRenderer, background_inputs_and_filter  # noqa: E402


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def project_duration_ms(root: Path) -> int:
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
    parser.add_argument("--run-id")
    parser.add_argument("--probe-seconds", type=float, default=2.0)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--keep", action="store_true", help="Keep the painted scratch states")
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    duration_ms = project_duration_ms(root)
    manifest = load(project / "input-manifest.json")
    presentation = load(project / "presentation.json")
    scenes = load(project / "scene-timeline.json")["segments"]
    canvas = manifest.get("outputs", [{"name": "16x9", "width": 1920, "height": 1080}])[0]
    width, height = int(canvas["width"]), int(canvas["height"])
    music = root / manifest["music"]["asset"]
    offset = int(manifest.get("alignment", {}).get("offsetMs", 0))

    if args.run_id:
        candidates = sorted((project / "work" / args.run_id).rglob("foreground-timeline.json"))
        timeline_path = candidates[0] if candidates else None
    else:
        flat = sorted(project.glob("work/*/*/foreground-timeline.json"), key=lambda path: path.stat().st_mtime)
        matches = flat or sorted((project / "work").rglob("foreground-timeline.json"), key=lambda path: path.stat().st_mtime)
        timeline_path = matches[-1] if matches else None
    if timeline_path is None:
        raise SystemExit("No foreground timeline found; run build_foreground_timeline.py first.")
    timeline = load(timeline_path)

    scratch = project / "work" / "preflight"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    renderer = ForegroundRenderer(root, width, height)

    states: list[tuple] = []
    for segment in timeline["segments"]:
        key = (segment["kind"], segment.get("frameId"), segment.get("activePartIndex"), segment.get("countdownValue"),
               segment.get("coverVisible", True))
        if key not in states:
            states.append(key)

    failures, started = [], time.time()
    for index, key in enumerate(states):
        kind, frame_id, active_index, countdown_value, cover_visible = key
        output = scratch / f"state-{index:05}.png"
        try:
            renderer.render(frame_id if kind != "blank" else None,
                            active_index if kind == "active" else None,
                            output, cover_only=kind == "cover", cover_visible=cover_visible,
                            countdown_value=countdown_value)
            if not output.is_file() or output.stat().st_size == 0:
                failures.append({"state": list(key), "error": "empty output"})
        except Exception as exc:  # noqa: BLE001 - report every state, never abort the sweep
            failures.append({"state": [value for value in key], "error": f"{type(exc).__name__}: {exc}"})
    paint_seconds = round(time.time() - started, 1)

    background_args, background_filter, background_count = background_inputs_and_filter(root, scenes, width, height, duration_ms)
    overlay = presentation.get("floatingOverlay", {})
    probe_output = scratch / "filtergraph-probe.mkv"
    sample = next(iter(sorted(scratch.glob("state-*.png"))), None)
    graph: dict = {"backgroundSegments": background_count, "spectrumEnabled": bool(overlay.get("enabled")), "result": "skipped"}
    if sample is not None:
        command = ["ffmpeg", "-y", "-v", "error", *background_args, "-loop", "1", "-i", str(sample)]
        spectrum_index = None
        if overlay.get("enabled"):
            spectrum = project / "work" / "setup-preview" / "foobar-spectrum.mov"
            if not spectrum.is_file():
                spectrum = next(iter(sorted((project / "work").rglob("foobar-spectrum.mov"), key=lambda path: path.stat().st_mtime)), None)
            if spectrum is not None:
                subprocess.run([sys.executable, str(SCRIPTS / "render_foobar_spectrum.py"), str(music),
                                str(project / "palette.json"), str(scratch / "spectrum.mov"),
                                "--duration-ms", str(round(args.probe_seconds * 1000)), "--offset-ms", str(offset)], check=True)
                command += ["-i", str(scratch / "spectrum.mov")]
                spectrum_index = background_count + 1
        command += ["-itsoffset", f"{offset / 1000:.6f}", "-i", str(music)]
        music_index = background_count + 1 + int(spectrum_index is not None)
        filters = [background_filter,
                   f"[{background_count}:v]fps=30,format=rgba,setpts=PTS-STARTPTS[foreground]",
                   "[background][foreground]overlay=0:0:format=auto[learning]"]
        if spectrum_index is not None:
            template = load(project / "templates" / "overlay.json")["render"]
            x, y = template["xPxAt1920x1080"], template["yPxAt1920x1080"]
            filters += [f"[{spectrum_index}:v]fps=30,format=rgba,setpts=PTS-STARTPTS[spectrum]",
                        f"[learning][spectrum]overlay={x}:{y}:format=auto,fps=30,format=yuv420p[video]"]
        else:
            filters += ["[learning]fps=30,format=yuv420p[video]"]
        command += ["-filter_complex", ";".join(filters), "-map", "[video]", "-map", f"{music_index}:a:0",
                    "-t", f"{args.probe_seconds:.3f}", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-r", "30", "-fps_mode", "cfr", "-c:a", "copy", str(probe_output)]
        probe = subprocess.run(command, capture_output=True, text=True)
        ok = probe.returncode == 0 and probe_output.is_file() and probe_output.stat().st_size > 0
        graph.update({"result": "passed" if ok else "failed", "stderr": "" if ok else probe.stderr.strip()[:1200]})
        if ok:
            streams = json.loads(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,bits_per_raw_sample",
                 "-of", "json", str(probe_output)], check=True, text=True, capture_output=True).stdout)["streams"]
            graph["outputStreams"] = streams
            audio = next((stream for stream in streams if stream["codec_type"] == "audio"), None)
            graph["audioPreservedAs"] = (f"{audio['codec_name']} {audio['sample_rate']} Hz "
                                        f"{audio.get('bits_per_raw_sample')}-bit {audio['channels']}ch") if audio else None

    report = {
        "schemaVersion": 1,
        "project": root.name,
        "timeline": str(timeline_path.relative_to(root)).replace("\\", "/"),
        "result": "passed" if not failures and graph.get("result") == "passed" else "failed",
        "statesPainted": len(states),
        "paintSeconds": paint_seconds,
        "estimatedFullPaintSeconds": paint_seconds,
        "layoutFailures": failures,
        "filterGraph": graph,
        "learningAids": resolve_options(presentation["foreground"]),
        "note": "Scratch states and the probe encode stay in project/work/preflight and are not deliverables.",
    }
    output = args.out or project / "qa" / "render-preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps({key: report[key] for key in ("result", "statesPainted", "paintSeconds", "layoutFailures", "filterGraph")},
                     ensure_ascii=False, indent=2))
    if report["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
