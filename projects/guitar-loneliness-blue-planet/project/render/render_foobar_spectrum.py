#!/usr/bin/env python3
"""Render the fixed transparent Foobar-style spectrum overlay."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def blend(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - ratio) + b[i] * ratio) for i in range(3))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("palette", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--duration-ms", type=int, required=True)
    parser.add_argument("--offset-ms", type=int, default=0)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    if args.duration_ms <= 0 or args.fps <= 0:
        raise SystemExit("duration and fps must be positive")

    project = Path(__file__).resolve().parents[1]
    template = load(project / "templates" / "overlay.json")["render"]
    palette = load(args.palette)
    width, height = template["widthPxAt1920x1080"], template["heightPxAt1920x1080"]
    bars = template["bars"]; sample_rate = template["analysisSampleRate"]; fft_size = template["fftSize"]
    frames = math.ceil(args.duration_ms / 1000 * args.fps)

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-err_detect", "ignore_err", "-i", str(args.audio), "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "f32le", "-"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    samples = np.frombuffer(raw, dtype=np.float32)
    shift = round(args.offset_ms / 1000 * sample_rate)
    if shift >= 0:
        samples = np.pad(samples, (shift, 0))
    else:
        samples = samples[min(len(samples), -shift):]
    required = round(args.duration_ms / 1000 * sample_rate) + fft_size
    if len(samples) < required:
        samples = np.pad(samples, (0, required - len(samples)))

    window = np.hanning(fft_size).astype(np.float32)
    low, high = template["frequencyRangeHz"]
    edges = np.geomspace(low, high, bars + 1)
    frequencies = np.fft.rfftfreq(fft_size, d=1 / sample_rate)
    bins = [(np.searchsorted(frequencies, edges[i]), max(np.searchsorted(frequencies, edges[i + 1]), np.searchsorted(frequencies, edges[i]) + 1)) for i in range(bars)]
    band_db = np.empty((frames, bars), dtype=np.float32)
    fft_norm = float(window.sum() / 2)
    for frame_index in range(frames):
        center = int((frame_index + 0.5) * sample_rate / args.fps)
        start = max(0, center - fft_size // 2)
        segment = samples[start:start + fft_size]
        if len(segment) < fft_size:
            segment = np.pad(segment, (0, fft_size - len(segment)))
        magnitude = np.abs(np.fft.rfft(segment * window)) / fft_norm + 1e-9
        band_db[frame_index] = [20 * np.log10(np.sqrt(np.mean(magnitude[left:right] ** 2))) for left, right in bins]

    percentile = template["referencePercentile"]
    gain_db = template["referenceDb"] - float(np.percentile(band_db, percentile))
    floor_db, ceiling_db = template["visibleDbRange"]
    attack, release = template["attack"], template["release"]
    peak_fall, height_scale = template["peakFallPerFrame"], template["heightScale"]
    levels = np.zeros(bars, dtype=np.float32); peaks = np.zeros(bars, dtype=np.float32)
    accent, hot = rgb(palette["accent"]), rgb(palette["activeTint"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}",
        "-r", str(args.fps), "-i", "-", "-an", "-c:v", "qtrle", "-pix_fmt", "argb", "-r", str(args.fps), str(args.output),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame_index in range(frames):
            target = np.clip((band_db[frame_index] + gain_db - floor_db) / (ceiling_db - floor_db), 0, 1) * height_scale
            rising = target > levels
            levels = np.where(rising, levels + (target - levels) * attack, levels + (target - levels) * release)
            peaks = np.maximum(levels, peaks - peak_fall)
            image = Image.new("RGBA", (width, height), (0, 0, 0, 0)); draw = ImageDraw.Draw(image)
            gap = 5; bar_width = (width - gap * (bars - 1)) / bars; baseline = height - 9
            for index, level in enumerate(levels):
                x0 = round(index * (bar_width + gap)); x1 = round(x0 + bar_width)
                bar_height = max(3, round(float(level) * 112)); y0 = baseline - bar_height
                draw.rounded_rectangle((x0, y0, x1, baseline), radius=2, fill=blend(accent, hot, float(level)) + (220,))
                peak_y = baseline - max(3, round(float(peaks[index]) * 112))
                draw.rectangle((x0, peak_y, x1, peak_y + 2), fill=hot + (240,))
            assert process.stdin is not None
            process.stdin.write(image.tobytes())
    finally:
        if process.stdin: process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("Transparent spectrum encoding failed")
    print(json.dumps({"output": str(args.output), "frames": frames, "bars": bars, "background": "transparent", "zIndex": "above-foreground"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
