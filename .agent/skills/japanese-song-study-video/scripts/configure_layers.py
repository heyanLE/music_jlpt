#!/usr/bin/env python3
"""Resolve a named layer preset into complete project JSON.

This script changes configuration only. It never edits frames or renders video.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from foreground_options import COUNTDOWN_PLACEMENTS, PRELUDE_MODES, configure_options


MINIMUM_TAIL_MS = 1000  # keep the cover-gaussian closing stage visible in the hybrid preset
PRESETS = ("video-loop-follow", "video-then-gaussian-hybrid", "gaussian-persistent", "custom")


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path}")
    return data


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(temp.read_text(encoding="utf-8"))
    temp.replace(path)


def duration_ms(path: Path) -> int:
    output = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout.strip()
    return round(float(output) * 1000)


def resolve_asset(project_root: Path, relative: str) -> Path:
    path = project_root / relative
    if not path.is_file():
        raise SystemExit(f"Frozen asset does not exist: {relative}")
    return path


def alignment(args: argparse.Namespace) -> dict:
    if args.offset_mode == "none":
        if args.offset_ms not in (None, 0):
            raise SystemExit("--offset-ms is valid only with --offset-mode manual")
        offset, evidence = 0, "explicit-none"
    elif args.offset_mode == "manual":
        if args.offset_ms is None:
            raise SystemExit("manual offset requires --offset-ms")
        offset, evidence = args.offset_ms, args.offset_reason or "user-specified"
    else:
        if not args.offset_report:
            raise SystemExit("onset offset requires --offset-report")
        report = load(args.offset_report)
        if report.get("result") != "usable" or report.get("confidence") not in ("medium", "high"):
            raise SystemExit("Onset report is not usable with medium/high confidence")
        offset, evidence = int(report["proposedOffsetMs"]), str(args.offset_report.resolve())
    return {
        "method": args.offset_mode,
        "offsetMs": offset,
        "definition": "signed output timestamp assigned to music time zero",
        "appliesTo": ["music", "lyrics", "spectrum"],
        "backgroundClock": "output",
        "evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--preset", required=True, choices=PRESETS)
    parser.add_argument("--spectrum", required=True, choices=("on", "off"))
    parser.add_argument("--background-asset", default="source/background.mp4")
    parser.add_argument("--cover-asset", default="source/cover.jpg")
    parser.add_argument("--transition-ms", default="auto", help="Hybrid hand-off in ms or auto=video duration")
    parser.add_argument("--fade-ms", type=int, default=500)
    parser.add_argument("--stage1-loop", action="store_true")
    parser.add_argument("--custom-scenes", type=Path)
    parser.add_argument("--offset-mode", choices=("none", "manual", "onset"), default="none")
    parser.add_argument("--offset-ms", type=int)
    parser.add_argument("--offset-reason")
    parser.add_argument("--offset-report", type=Path)
    parser.add_argument("--line-translation", choices=("on", "off"), default="on")
    parser.add_argument("--learning-assist", choices=("on", "off"), help="Set both neighbors and countdown; individual switches take precedence")
    parser.add_argument("--neighbors", choices=("on", "off"), help="New project default: on; existing value preserved when omitted")
    parser.add_argument("--countdown", choices=("on", "off"), help="3/2/1 before first sung QRC unit; new project default: on")
    parser.add_argument("--prelude-mode", choices=PRELUDE_MODES, help="New project default: first-line; independent of lyric-gap mode")
    parser.add_argument("--countdown-placement", choices=COUNTDOWN_PLACEMENTS,
                        help="template (upper-right) or neighbor-left (the free previous-line slot beside the first line)")
    args = parser.parse_args()

    root = args.project_root.resolve(); project = root / "project"
    manifest_path = project / "input-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing {manifest_path}")
    manifest = load(manifest_path)
    existing_path = project / "presentation.json"
    existing = load(existing_path).get("foreground", {}) if existing_path.is_file() else None
    learning_aids = configure_options(existing, args.neighbors or args.learning_assist, args.countdown or args.learning_assist,
                                      args.prelude_mode, args.countdown_placement)
    cover = resolve_asset(root, args.cover_asset)
    if args.fade_ms < 0 or args.fade_ms > 3000:
        raise SystemExit("--fade-ms must be 0..3000")

    if args.preset == "custom":
        if not args.custom_scenes:
            raise SystemExit("custom preset requires --custom-scenes")
        custom = load(args.custom_scenes)
        segments = custom.get("segments")
        if not isinstance(segments, list) or not segments:
            raise SystemExit("custom scene file requires a non-empty segments array")
        # Documentation travels with the schedule: the renderer accepts a hand-authored
        # timeline only when it carries a note, and the note explains why no preset fits.
        custom_note = str(custom.get("note", "")).strip()
        if not custom_note:
            raise SystemExit("custom scene file needs a note explaining the schedule")
        for segment in segments:
            required = {"id", "startMs", "endMs", "mode", "foregroundMode"}
            missing = required - segment.keys()
            if missing:
                raise SystemExit(f"Custom scene {segment.get('id', '?')} missing {sorted(missing)}")
    elif args.preset == "video-loop-follow":
        resolve_asset(root, args.background_asset)
        segments = [{
            "id": "main-video-loop", "startMs": 0, "endMs": "audio-end", "mode": "video-loop",
            "asset": args.background_asset, "fit": "height-center-pillarbox", "sourceAudio": "mute",
            "foregroundMode": "follow-lyrics", "transitionIn": {"kind": "none", "durationMs": 0, "scope": "background-only"},
            "transitionOut": {"kind": "none", "durationMs": 0, "scope": "background-only"},
        }]
    elif args.preset == "gaussian-persistent":
        segments = [{
            "id": "main-cover-gaussian", "startMs": 0, "endMs": "audio-end", "mode": "cover-gaussian",
            "asset": args.cover_asset, "foregroundMode": "persistent",
            "transitionIn": {"kind": "none", "durationMs": 0, "scope": "background-only"},
            "transitionOut": {"kind": "none", "durationMs": 0, "scope": "background-only"},
        }]
    else:
        background = resolve_asset(root, args.background_asset)
        source_duration = duration_ms(background)
        handoff = source_duration if args.transition_ms == "auto" else int(args.transition_ms)
        if handoff <= 0:
            raise SystemExit("Hybrid transition must be positive")
        if handoff > source_duration and not args.stage1_loop:
            raise SystemExit("Hybrid transition exceeds video duration; add --stage1-loop or choose an earlier time")
        # A video at least as long as the song leaves the cover-gaussian stage zero length,
        # which renders nothing and used to abort the render. The preset promises "video,
        # then blurred cover", so the video's tail is trimmed to keep that closing stage
        # visible; the trim is recorded in the scene timeline and the manifest.
        output_end = duration_ms(resolve_asset(root, manifest["music"]["asset"])) + (args.offset_ms or 0)
        trimmed_ms = 0
        if not args.stage1_loop and output_end - handoff < MINIMUM_TAIL_MS:
            trimmed_ms = handoff - max(0, output_end - MINIMUM_TAIL_MS)
            handoff = max(0, output_end - MINIMUM_TAIL_MS)
            if handoff <= 0:
                raise SystemExit("The output is shorter than the minimum cover tail; check the music and offset")
        fade = {"kind": "black-fade" if args.fade_ms else "none", "durationMs": args.fade_ms, "scope": "background-only"}
        segments = [
            {
                "id": "stage1-video", "startMs": 0, "endMs": handoff,
                "mode": "video-loop" if args.stage1_loop else "video-clip", "asset": args.background_asset,
                "fit": "height-center-pillarbox", "sourceAudio": "mute", "foregroundMode": "follow-lyrics",
                "transitionIn": {"kind": "none", "durationMs": 0, "scope": "background-only"}, "transitionOut": fade,
                **({"tailTrimmedMs": trimmed_ms} if trimmed_ms else {}),
            },
            {
                "id": "stage2-cover-gaussian", "startMs": handoff, "endMs": "audio-end", "mode": "cover-gaussian",
                "asset": args.cover_asset, "foregroundMode": "persistent", "transitionIn": fade,
                "transitionOut": {"kind": "none", "durationMs": 0, "scope": "background-only"},
            },
        ]
        if trimmed_ms:
            print(json.dumps({"hybridTailTrimmedMs": trimmed_ms, "videoStageEndMs": handoff,
                              "reason": "the video is at least as long as the song; the tail is trimmed so the "
                                        f"cover-gaussian closing stage keeps at least {MINIMUM_TAIL_MS} ms"},
                             ensure_ascii=False))

    align = alignment(args)
    manifest["schemaVersion"] = max(4, int(manifest.get("schemaVersion", 1)))
    manifest["pipelinePreset"] = args.preset
    manifest["alignment"] = align
    write(manifest_path, manifest)
    scene_document = {"schemaVersion": 2, "clock": "output", "preset": args.preset, "segments": segments}
    if args.preset == "custom":
        scene_document["note"] = custom_note
    write(project / "scene-timeline.json", scene_document)
    overlay_on = args.spectrum == "on"
    presentation = {
        "schemaVersion": 3,
        "foreground": {
            **learning_aids,
            "templateId": "study-current-v3", "defaultMode": segments[0]["foregroundMode"],
            "displayTiming": {"preRollMs": 0, "tailProtectionMs": 500, "internalGap": "hold-current-line"},
            "lineTranslation": {"enabled": args.line_translation == "on"},
            "veil": {"color": "#000000", "opacity": 0.28},
            "highlight": {"mode": "token" if manifest.get("lyrics", {}).get("format") == "qq-music" else "line"},
            "textOutline": {"enabled": True, "color": "#000000"},
        },
        "floatingOverlay": {
            "id": "spectrum-foobar-bars" if overlay_on else "none", "enabled": overlay_on,
            "persistent": True, "zIndex": "above-foreground", "clock": "output",
        },
    }
    write(project / "presentation.json", presentation)

    skill = Path(__file__).resolve().parents[1]
    snapshots = project / "templates"; snapshots.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(skill / "templates" / "foreground" / "study-current-v3.json", snapshots / "foreground.json")
    write(snapshots / "background.json", {
        "schemaVersion": 2,
        "id": f"resolved-{args.preset}",
        "owns": "background-only",
        "sourceTemplate": "templates/background/pipeline-presets-v1.json",
        "segments": segments,
    })
    shutil.copyfile(skill / "templates" / "overlays" / ("spectrum-foobar-bars.json" if overlay_on else "none.json"), snapshots / "overlay.json")

    state_path = project / "build-state.json"
    state = load(state_path) if state_path.is_file() else {"schemaVersion": 2, "notes": []}
    state.update({"stage": "inputs_confirmed", "renderAuthorization": False})
    state.setdefault("notes", []).append(f"Layer configuration resolved by configure_layers.py: {args.preset}; spectrum={args.spectrum}; offsetMs={align['offsetMs']}.")
    write(state_path, state)
    print(json.dumps({"preset": args.preset, "spectrum": overlay_on, "offsetMs": align["offsetMs"], "segments": len(segments)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
