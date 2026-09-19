#!/usr/bin/env python3
"""Shared helpers for composing real-content QA stills from a project's own assets.

Both render_real_previews.py and build_review_gallery.py draw the same thing: one
frame of the finished video (background + foreground + floating spectrum) at a
given output time. Keeping the composition here means the two callers cannot
drift apart, and every project gets the renderer's real geometry instead of a
re-implementation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

BACKGROUND_FILTER = "fps=30,scale=-2:{height},crop='min(iw,{width})':{height},pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def probe_duration_seconds(path: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout.strip())


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def extract(source: Path, seconds: float, output: Path, filters: str = "", seek_seconds: float | None = None) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    # A still image needs -loop 1 to emit a frame once a filter chain is applied;
    # otherwise ffmpeg reports "No filtered frames" and writes nothing.
    if source.suffix.lower() in IMAGE_SUFFIXES:
        command += ["-loop", "1"]
    command += ["-ss", f"{(seek_seconds if seek_seconds is not None else seconds):.6f}"]
    command += ["-i", str(source)]
    if filters:
        command += ["-vf", filters]
    subprocess.run(command + ["-frames:v", "1", "-update", "1", str(output)], check=True)
    if not output.is_file():
        raise SystemExit(f"Extracted frame was not written: {output}")


class ProjectStill:
    """Resolve a project's assets and compose finished-video stills."""

    def __init__(self, root: Path, timeline_path: Path | None = None, spectrum_path: Path | None = None,
                 run_id: str | None = None, width: int = 1920, height: int = 1080):
        self.root = root.resolve()
        self.project = self.root / "project"
        self.width, self.height = width, height
        self.manifest = load(self.project / "input-manifest.json")
        self.presentation = load(self.project / "presentation.json")
        self.frames = load(self.project / "frames.json")["frames"]
        self.background = self.root / self.manifest["backgroundAsset"]
        self.video_seconds = probe_duration_seconds(self.background)
        self.timeline_path = timeline_path or self.default_timeline(run_id)
        self.timeline = load(self.timeline_path) if self.timeline_path and self.timeline_path.is_file() else None
        self.spectrum = spectrum_path
        if self.spectrum is None:
            self.spectrum = self.default_spectrum(run_id)

    # -- asset discovery ------------------------------------------------------
    def default_timeline(self, run_id: str | None) -> Path | None:
        if run_id:
            candidate = self.project / "work" / run_id
            matches = sorted(candidate.rglob("foreground-timeline.json"))
            if matches:
                return matches[0]
        # Prefer the flat render-run layout (work/<runId>/<canvas>/foreground-timeline.json)
        # so a scratch tree buried deeper in work/ can never win, then fall back to
        # the newest match anywhere for projects that keep another layout.
        flat = sorted(self.project.glob("work/*/*/foreground-timeline.json"), key=lambda path: path.stat().st_mtime)
        if flat:
            return flat[-1]
        matches = sorted((self.project / "work").rglob("foreground-timeline.json"), key=lambda path: path.stat().st_mtime)
        return matches[-1] if matches else None

    def default_spectrum(self, run_id: str | None) -> Path | None:
        if run_id:
            matches = sorted((self.project / "work" / run_id).rglob("foobar-spectrum.mov"))
            if matches:
                return matches[0]
        flat = sorted(self.project.glob("work/*/*/foobar-spectrum.mov"), key=lambda path: path.stat().st_mtime)
        if flat:
            return flat[-1]
        matches = sorted((self.project / "work").rglob("foobar-spectrum.mov"), key=lambda path: path.stat().st_mtime)
        return matches[-1] if matches else None

    def require_timeline(self) -> dict:
        if self.timeline is None:
            raise SystemExit(
                "No foreground timeline found. Run build_foreground_timeline.py first "
                "(or pass --timeline), so previews show the state the renderer really paints."
            )
        return self.timeline

    # -- state lookup ---------------------------------------------------------
    def segment_at(self, timestamp_ms: int) -> dict:
        for segment in self.require_timeline()["segments"]:
            if segment["startMs"] <= timestamp_ms < segment["endMs"]:
                return segment
        raise SystemExit(f"No foreground segment covers {timestamp_ms} ms")

    def representative_ms(self, frame_id: str, prefer: str = "active") -> int:
        segments = self.require_timeline()["segments"]
        for kind in (prefer, "neutral", "blank", "cover"):
            for segment in segments:
                if segment.get("frameId") == frame_id and segment["kind"] == kind:
                    return (segment["startMs"] + segment["endMs"]) // 2
        raise SystemExit(f"Frame {frame_id} is never displayed in this timeline")

    def render_foreground(self, renderer, segment: dict) -> Image.Image:
        return renderer.render(
            segment.get("frameId"),
            segment.get("activePartIndex") if segment["kind"] == "active" else None,
            None,
            cover_only=segment["kind"] == "cover",
            cover_visible=segment.get("coverVisible", True),
            countdown_value=segment.get("countdownValue"),
        )

    # -- composition ----------------------------------------------------------
    def background_image(self, seconds: float, work: Path, stem: str) -> Image.Image:
        """Compose the background exactly as the schedule says it will appear.

        The scene timeline decides which asset is on screen - a pre-roll still, a video
        segment offset by its start time, or the blurred cover - so previews match the
        finished video for every preset, not only the single-asset ones.
        """
        timeline_path = self.project / "scene-timeline.json"
        scenes = load(timeline_path)["segments"] if timeline_path.is_file() else []
        moment_ms = round(seconds * 1000)
        scene = None
        for candidate in scenes:
            end = candidate["endMs"]
            if candidate["startMs"] <= moment_ms and (end == "audio-end" or moment_ms < int(end)):
                scene = candidate
                break
        path = work / f"{stem}-background.png"
        if scene is None:
            extract(self.background, seconds, path, BACKGROUND_FILTER.format(width=self.width, height=self.height),
                    seek_seconds=seconds % self.video_seconds)
            return Image.open(path).convert("RGBA")
        asset = (self.root / scene["asset"]).resolve()
        if scene["mode"] == "cover-gaussian":
            extract(asset, 0, path, f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
                                    f"crop={self.width}:{self.height},gblur=sigma=30,eq=brightness=-0.25", seek_seconds=0)
            return Image.open(path).convert("RGBA")
        if scene["mode"] in ("video-clip", "video-loop"):
            local = (moment_ms - int(scene["startMs"])) / 1000
            asset_seconds = probe_duration_seconds(asset)
            seek = local % asset_seconds if (scene["mode"] == "video-loop" or asset_seconds <= local) else local
            extract(asset, max(0.0, seek), path, BACKGROUND_FILTER.format(width=self.width, height=self.height),
                    seek_seconds=max(0.0, seek))
            return Image.open(path).convert("RGBA")
        raise SystemExit(f"Preview cannot compose background mode {scene['mode']}")

    def compose(self, renderer, foreground: Image.Image, seconds: float, output: Path, with_spectrum: bool = True) -> None:
        work = output.parent / "_work"
        work.mkdir(parents=True, exist_ok=True)
        image = self.background_image(seconds, work, output.stem)
        image.alpha_composite(foreground)
        if with_spectrum and self.spectrum and self.spectrum.is_file():
            spectrum_frame = work / f"{output.stem}-spectrum.png"
            extract(self.spectrum, seconds, spectrum_frame, "format=rgba")
            template = load(self.project / "templates" / "overlay.json")["render"]
            x = round(template["xPxAt1920x1080"] * self.width / 1920)
            y = round(template["yPxAt1920x1080"] * self.height / 1080)
            image.alpha_composite(Image.open(spectrum_frame).convert("RGBA"), (x, y))
        output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(output)
        for stale in (work / f"{output.stem}-background.png", work / f"{output.stem}-spectrum.png"):
            stale.unlink(missing_ok=True)

    def still(self, renderer, frame_id: str | None, output: Path, seconds: float | None = None, with_spectrum: bool = True) -> dict:
        """Compose one still. ``frame_id=None`` means 'whatever state is on screen at ``seconds``'."""
        timestamp_ms = round(seconds * 1000) if seconds is not None else self.representative_ms(frame_id)
        segment = self.segment_at(timestamp_ms)
        foreground = self.render_foreground(renderer, segment)
        self.compose(renderer, foreground, timestamp_ms / 1000, output, with_spectrum=with_spectrum)
        return {
            "frameId": segment.get("frameId"),
            "requestedFrameId": frame_id,
            "outputSeconds": round(timestamp_ms / 1000, 3),
            "foregroundState": {key: value for key, value in segment.items()
                                if key in ("kind", "frameId", "activePartIndex", "countdownValue", "coverVisible")},
            "path": str(output).replace("\\", "/"),
            "relativePath": str(output.resolve().relative_to(self.root)).replace("\\", "/")
            if output.resolve().is_relative_to(self.root) else str(output).replace("\\", "/"),
        }


def load_renderer(root: Path, width: int = 1920, height: int = 1080):
    """The fixed-preset foreground renderer, imported from the skill."""
    scripts = Path(__file__).resolve().parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from render_video import ForegroundRenderer  # noqa: E402 - sibling import
    return ForegroundRenderer(root, width, height)
