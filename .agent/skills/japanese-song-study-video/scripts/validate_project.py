#!/usr/bin/env python3
"""Validate core Japanese song project artifacts without modifying them.

Usage: python validate_project.py PROJECT_ROOT --stage setup|draft|render
"""
from __future__ import annotations

import argparse, hashlib, json
from pathlib import Path

from verify_render_gate import verify_render_gate
from foreground_options import resolve_options


def json_file(path: Path) -> dict:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM is forbidden: {path}")
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid UTF-8 JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Top level must be object: {path}")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--stage", required=True, choices=("setup", "draft", "render"))
    parser.add_argument("--renderer", type=Path, help="Actual selected renderer; defaults to bundled entrypoint")
    args = parser.parse_args(); project = args.project_root / "project"
    required = [project / "input-manifest.json", project / "presentation.json", project / "scene-timeline.json", project / "build-state.json"]
    if args.stage != "setup": required += [project / "frames.json", project / "render" / "resolved-layout.json"]
    data = {path.name: json_file(path) for path in required}
    scene = data["scene-timeline.json"]
    previous_end = 0
    seen_audio_end = False
    for segment in scene.get("segments", []):
        if seen_audio_end: raise ValueError("No scene may follow audio-end")
        if segment.get("startMs") != previous_end:
            raise ValueError("Scene segments must be contiguous from output-clock zero")
        if segment.get("mode") not in ("video-loop", "video-clip", "cover-gaussian", "still-cover", "solid"):
            raise ValueError(f"Invalid background mode: {segment.get('mode')}")
        if scene.get("schemaVersion", 1) >= 2 and segment.get("foregroundMode") not in ("follow-lyrics", "persistent"):
            raise ValueError(f"Scene foregroundMode missing/invalid: {segment.get('id')}")
        asset = segment.get("asset")
        if asset and not (args.project_root / asset).is_file():
            raise ValueError(f"Scene references an unfrozen/missing asset: {asset}")
        end = segment.get("endMs")
        if isinstance(end, int): previous_end = end
        elif end == "audio-end": seen_audio_end = True
        else: raise ValueError("endMs must be int or audio-end")
    if not scene.get("segments"): raise ValueError("At least one scene segment is required")
    manifest = data["input-manifest.json"]
    alignment = manifest.get("alignment", {})
    if manifest.get("schemaVersion", 1) >= 4:
        if alignment.get("method") not in ("none", "manual", "onset") or not isinstance(alignment.get("offsetMs"), int):
            raise ValueError("alignment requires method none|manual|onset and signed integer offsetMs")
        if alignment.get("appliesTo") != ["music", "lyrics", "spectrum"]:
            raise ValueError("alignment must apply together to music, lyrics, and spectrum")
    presentation_doc = data["presentation.json"]
    presentation = presentation_doc.get("foreground", {})
    resolve_options(presentation)
    if presentation_doc.get("schemaVersion", 1) >= 3:
        missing_options = {"neighbors", "countdown", "preludeMode"} - presentation.keys()
        if missing_options: raise ValueError(f"Presentation v3 requires explicit learning-aid fields: {sorted(missing_options)}")
    if presentation.get("highlight", {}).get("mode") not in ("token", "kana", "line", "none"):
        raise ValueError("Invalid highlight mode")
    opacity = presentation.get("veil", {}).get("opacity", 0)
    if not 0 <= opacity <= .85: raise ValueError("Veil opacity must be 0..0.85")
    default_mode = presentation.get("defaultMode")
    legacy_visible = presentation.get("visibleDuringNoLyric")
    if default_mode is not None and default_mode not in ("follow-lyrics", "persistent"):
        raise ValueError("foreground.defaultMode must be follow-lyrics or persistent")
    if default_mode is None and legacy_visible is None:
        raise ValueError("Foreground visibility policy is missing")
    timing = presentation.get("displayTiming", {})
    if default_mode is not None:
        if timing.get("internalGap") != "hold-current-line":
            raise ValueError("Foreground internalGap must be hold-current-line")
        if timing.get("tailProtectionMs") != 500:
            raise ValueError("follow-lyrics tailProtectionMs must be exactly 500")
    overlay = presentation_doc.get("floatingOverlay", {})
    if overlay.get("enabled"):
        if overlay.get("id") != "spectrum-foobar-bars" or overlay.get("zIndex") != "above-foreground":
            raise ValueError("Enabled spectrum must use spectrum-foobar-bars above foreground")
        if not overlay.get("persistent"):
            raise ValueError("Enabled spectrum must be persistent")
    if args.stage != "setup":
        for frame in data["frames.json"].get("frames", []):
            for card in frame.get("grammarCards", []):
                if bool(card.get("zhMeaning")) == bool(card.get("functionZh")):
                    raise ValueError(f"Card must have exactly one meaning/function: {frame.get('id')}")
                grammar = card.get("grammarStructureZh") or card.get("posZh")
                if not card.get("token") or not grammar:
                    raise ValueError(f"Card token/grammar structure missing: {frame.get('id')}")
                if "|" in "".join(str(v) for v in card.values()):
                    raise ValueError(f"Serialized card separator: {frame.get('id')}")
    if args.stage == "render":
        authorization_path = project / "render-authorization.json"
        if not authorization_path.is_file():
            raise ValueError("Explicit render authorization is missing")
        authorization = json_file(authorization_path)
        selected_renderer = (args.renderer or Path(__file__).with_name("render_video.py")).resolve()
        verify_render_gate(args.project_root.resolve(), selected_renderer)
    print(f"PASS {args.stage}: {args.project_root}")


if __name__ == "__main__":
    main()
