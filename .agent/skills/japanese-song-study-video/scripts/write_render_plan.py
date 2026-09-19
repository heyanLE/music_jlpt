#!/usr/bin/env python3
"""Write project/render/render-plan.json: what exactly is about to be rendered.

The plan records the run id, the selected renderer, the enabled features, the
audio policy and every hash the render authorization will bind, so a later reader
can tell whether a candidate came from the content currently on disk.

Usage
    python write_render_plan.py PROJECT_ROOT --run-id ID [--renderer FILE]
        [--authorization-text TEXT] [--out FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

BUNDLED_RENDERER = Path(__file__).resolve().with_name("render_video.py")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duration_seconds(path: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--renderer", type=Path)
    parser.add_argument("--authorization-text")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.project_root.resolve()
    project = root / "project"
    manifest = load(project / "input-manifest.json")
    presentation = load(project / "presentation.json")
    foreground = presentation["foreground"]
    scene = load(project / "scene-timeline.json")
    frames = load(project / "frames.json")["frames"]
    renderer = (args.renderer or BUNDLED_RENDERER).resolve()
    canvas = manifest.get("outputs", [{"name": "16x9", "width": 1920, "height": 1080, "fps": 30}])[0]
    music = root / manifest["music"]["asset"]
    offset = int(manifest.get("alignment", {}).get("offsetMs", 0))
    duration_ms = round(duration_seconds(music) * 1000) + offset
    audio = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate,channels,bits_per_raw_sample", "-of", "json", str(music)],
        check=True, text=True, capture_output=True,
    ).stdout)["streams"][0]

    first_scene = scene["segments"][0]
    overlay = presentation.get("floatingOverlay", {})
    learning = {
        "neighbors": foreground.get("neighbors", {}).get("enabled", False),
        "countdown": foreground.get("countdown", {}),
        "preludeMode": foreground.get("preludeMode"),
    }
    qa_required = ["probe-duration-resolution-fps", "audio-stream-copy", "first-last-lyric",
                   "maximum-cards", "mixed-language", "pure-english", "gap", "tail", "transitions"]
    if learning["neighbors"]:
        qa_required.append("neighbor-boundaries")
    if learning["countdown"].get("enabled"):
        qa_required.append("countdown-3-2-1")
    if foreground.get("preludeMode") == "first-line":
        qa_required.append("prelude-first-line")
    if overlay.get("enabled"):
        qa_required.append("spectrum-transparency-persistence")
    if first_scene.get("mode") == "video-loop":
        qa_required.append("loop-seam")
    if any(frame.get("caption", {}).get("furigana") for frame in frames):
        qa_required.append("kanji-ruby")
    if any(card.get("sourceWord") for frame in frames for card in frame.get("grammarCards", [])):
        qa_required.append("loanword")

    plan = {
        "schemaVersion": 2,
        "state": "ready-for-explicitly-authorized-render",
        "runId": args.run_id,
        "authorizationText": args.authorization_text,
        "entryPoint": str(renderer),
        "rendererSha256": sha(renderer),
        "backgroundPreset": manifest.get("pipelinePreset"),
        "background": {
            "asset": manifest.get("backgroundAsset"),
            "mode": first_scene.get("mode"),
            "sourceAudio": first_scene.get("sourceAudio", "mute"),
            "transition": first_scene.get("transitionOut", {}).get("kind", "none"),
            "durationSeconds": round(duration_seconds(root / manifest["backgroundAsset"]), 3)
            if manifest.get("backgroundAsset") else None,
        },
        "layers": ["background", "foreground", "floatingOverlay" if overlay.get("enabled") else "floatingOverlay-disabled"],
        "learningAids": learning,
        "spectrum": {"id": overlay.get("id"), "enabled": bool(overlay.get("enabled")),
                     "persistent": overlay.get("persistent"), "transparent": True, "clock": overlay.get("clock")},
        "audio": {
            "asset": manifest["music"]["asset"], "codec": audio["codec_name"],
            "sampleRate": int(audio["sample_rate"]), "channels": int(audio["channels"]),
            "bitsPerSample": int(audio["bits_per_raw_sample"]) if audio.get("bits_per_raw_sample") else None,
            "operation": "stream-copy", "container": "matroska", "durationMs": duration_ms, "offsetMs": offset,
        },
        "outputs": [{
            "name": canvas["name"], "width": canvas["width"], "height": canvas["height"], "fps": canvas.get("fps", 30),
            "candidate": f"project/work/{args.run_id}/{canvas['name']}/{manifest.get('slug', root.name)}--{canvas['name']}--{args.run_id}.mkv",
        }],
        "activeHashes": {
            key: sha(path) for key, path in {
                "inputManifest": project / "input-manifest.json",
                "sourceManifest": root / "source" / "source-manifest.json",
                "frames": project / "frames.json",
                "palette": project / "palette.json",
                "presentation": project / "presentation.json",
                "sceneTimeline": project / "scene-timeline.json",
                "foregroundTemplate": project / "templates" / "foreground.json",
                "overlayTemplate": project / "templates" / "overlay.json",
                "reviewDecision": project / "review" / "review-decision.json",
                "mergeLog": project / "review" / "merge-log.json",
                "assistedReviewAudit": project / "review" / "assisted-review-audit.json",
            }.items() if path.is_file()
        },
        "content": {
            "frames": len(frames),
            "cards": sum(len(frame.get("grammarCards", [])) for frame in frames),
            "englishRows": [frame["id"] for frame in frames if not frame.get("grammarCards")],
        },
        "qaRequired": qa_required,
    }
    output = args.out or project / "render" / "render-plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(output.read_text(encoding="utf-8"))
    print(json.dumps({"plan": str(output.relative_to(root)).replace("\\", "/"), "runId": args.run_id,
                      "candidate": plan["outputs"][0]["candidate"], "qaRequired": qa_required}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
