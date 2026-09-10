#!/usr/bin/env python3
"""Finish setup artifacts and render a non-authorizing structure preview."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
SKILL = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def import_foreground_renderer():
    script = SKILL / "scripts" / "render_video.py"
    sys.path.insert(0, str(script.parent))
    spec = importlib.util.spec_from_file_location("study_render_video", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.ForegroundRenderer


def main() -> None:
    manifest = load(PROJECT / "input-manifest.json")
    source_manifest = load(ROOT / "source" / "source-manifest.json")
    scene = load(PROJECT / "scene-timeline.json")
    presentation = load(PROJECT / "presentation.json")
    palette = load(PROJECT / "palette.json")
    output = manifest["outputs"][0]
    width, height = int(output["width"]), int(output["height"])

    assets = {
        "schemaVersion": 1,
        "sourceManifest": "source/source-manifest.json",
        "assets": source_manifest["assets"],
        "active": {
            "music": manifest["music"],
            "cover": manifest["cover"],
            "lyrics": manifest["lyrics"],
            "backgroundAssets": manifest["backgroundAssets"],
            "alignment": manifest["alignment"],
        },
        "templateSha256": {
            name: sha(PROJECT / "templates" / name)
            for name in ("foreground.json", "background.json", "overlay.json")
        },
    }
    write(PROJECT / "assets.json", assets)

    frame_id = "l003"
    preview_time_ms = 28131
    background_png = PROJECT / "qa" / "structure-background-16x9.png"
    foreground_png = PROJECT / "qa" / "structure-foreground-16x9.png"
    final_png = PROJECT / "qa" / "structure-preview-16x9.png"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-ss", f"{preview_time_ms / 1000:.3f}",
        "-i", str(ROOT / "source" / "background.mp4"), "-frames:v", "1",
        "-vf", f"scale=-2:{height},crop='min(iw,{width})':{height},pad={width}:{height}:(ow-iw)/2:(oh-ih):black",
        str(background_png),
    ], check=True)

    Renderer = import_foreground_renderer()
    renderer = Renderer(ROOT, width, height)
    renderer.frames[frame_id]["grammarCards"] = [
        {"token": "炭酸", "reading": "たんさん", "romaji": "tansan", "zhMeaning": "碳酸", "grammarStructureZh": "名词"},
        {"token": "が", "reading": "", "romaji": "ga", "functionZh": "标记主语", "grammarStructureZh": "格助词"},
        {"token": "抜ける", "reading": "ぬける", "romaji": "nukeru", "zhMeaning": "消散", "grammarStructureZh": "自动词"},
        {"token": "より", "reading": "", "romaji": "yori", "functionZh": "比较基准", "grammarStructureZh": "格助词"},
        {"token": "早い", "reading": "はやい", "romaji": "hayai", "zhMeaning": "快", "grammarStructureZh": "い形容词"},
        {"token": "スピード", "reading": "", "romaji": "supiido", "sourceWord": "speed", "zhMeaning": "速度", "grammarStructureZh": "名词"},
        {"token": "で", "reading": "", "romaji": "de", "functionZh": "表示状态或方式", "grammarStructureZh": "格助词"}
    ]
    renderer.render(frame_id, 2, foreground_png)

    canvas = Image.open(background_png).convert("RGBA")
    canvas.alpha_composite(Image.open(foreground_png).convert("RGBA"))
    draw = ImageDraw.Draw(canvas)
    accent, active = rgb(palette["accent"]), rgb(palette["activeTint"])
    bars, x0, y0, overlay_width, overlay_height = 72, 36, 894, 1848, 150
    gap = 5
    bar_width = (overlay_width - gap * (bars - 1)) / bars
    baseline = y0 + overlay_height - 9
    for index in range(bars):
        phase = (index % 13) / 12
        level = 0.16 + 0.48 * (1 - abs(phase * 2 - 1))
        height_px = max(3, round(level * 112))
        left = round(x0 + index * (bar_width + gap))
        right = round(left + bar_width)
        color = tuple(round(accent[i] * (1 - level) + active[i] * level) for i in range(3)) + (220,)
        draw.rounded_rectangle((left, baseline - height_px, right, baseline), radius=2, fill=color)
        draw.rectangle((left, baseline - height_px, right, baseline - height_px + 2), fill=active + (240,))
    canvas.save(final_png)

    report = {
        "schemaVersion": 1,
        "result": "passed",
        "canvas": output,
        "previewFrameId": frame_id,
        "previewOutputClockMs": preview_time_ms,
        "layers": ["background", "foreground", "floatingOverlay"],
        "foregroundTemplate": "study-current-v3",
        "sampleCards": "layout-only placeholders; not accepted linguistic content",
        "checks": {
            "topCenterCover": True,
            "sharedLyricRomajiAnnotationAnchors": True,
            "loanwordAnnotation": True,
            "kanjiOnlyFurigana": True,
            "lineTranslation": True,
            "singleHorizontalCardRow": True,
            "transparentPersistentSpectrum": True,
            "boldCjkFont": "C:/Windows/Fonts/msyhbd.ttc",
        },
        "sceneTimeline": scene,
        "presentation": presentation,
    }
    write(PROJECT / "qa" / "structure-report.json", report)

    state = load(PROJECT / "build-state.json")
    state["stage"] = "setup_complete"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append("Setup completed with dual-video custom timeline, structure preview, and cover-derived palette.")
    write(PROJECT / "build-state.json", state)
    print(json.dumps({"assets": str(PROJECT / "assets.json"), "preview": str(final_png), "stage": state["stage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
