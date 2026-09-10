"""Build a transparent-keyed foobar2000-style segmented spectrum from the frozen music."""
import argparse
import json
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
PROJECT = ROOT / "project"
FPS, SAMPLE_RATE = 30, 8000
BARS, FFT_SIZE = 84, 2048


def mix(a, b, amount):
    return tuple(round(a[i] * (1 - amount) + b[i] * amount) for i in range(3))


def rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True)
    args = parser.parse_args()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    palette = json.loads((PROJECT / "palette.json").read_text(encoding="utf-8"))
    config = json.loads((PROJECT / "templates" / "background.json").read_text(encoding="utf-8"))["spectrumOverlay"]
    width, height = config["placement"]["widthPx"], config["placement"]["heightPx"]
    analysis = config["audioAnalysis"]
    accent, hot = rgb(palette["accent"]), rgb(palette["activeTint"])
    peak = mix(hot, (255, 255, 255), 0.45)
    pcm, output = work / "mono-8k.f32le", work / "foobar-spectrum.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(SOURCE / "music.flac"), "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", str(pcm)], check=True)
    samples = np.fromfile(pcm, dtype=np.float32)
    frame_count = math.ceil(len(samples) / SAMPLE_RATE * FPS)
    window, edges = np.hanning(FFT_SIZE), np.geomspace(2, FFT_SIZE // 2, BARS + 1).astype(int)
    level, peak_level = np.zeros(BARS), np.zeros(BARS)
    process = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr", str(output)], stdin=subprocess.PIPE)
    gap = 6
    bar_width = (width - gap * (BARS - 1)) // BARS
    segment_height, segment_gap = 3, 2
    steps = max(1, height // (segment_height + segment_gap) - 1)
    try:
        for frame in range(frame_count):
            center = int(frame / FPS * SAMPLE_RATE)
            raw = np.zeros(FFT_SIZE, dtype=np.float32)
            start, end = max(0, center - FFT_SIZE // 2), min(len(samples), center + FFT_SIZE // 2)
            offset = start - (center - FFT_SIZE // 2)
            raw[offset:offset + end - start] = samples[start:end]
            magnitude = np.abs(np.fft.rfft(raw * window))
            bands = np.array([magnitude[edges[i]:max(edges[i] + 1, edges[i + 1])].mean() for i in range(BARS)])
            target = np.clip(np.log1p(bands * analysis["gain"]) / analysis["normalizer"], 0.02, 1)
            level = np.where(target > level, level + (target - level) * analysis["attack"], level + (target - level) * analysis["release"])
            peak_level = np.maximum(peak_level - analysis["peakDecay"], level)
            image = Image.new("RGB", (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(image)
            for index, value in enumerate(level):
                x = index * (bar_width + gap)
                count = max(1, int(1 + value * steps))
                for step in range(count):
                    bottom = height - 1 - step * (segment_height + segment_gap)
                    draw.rectangle((x, bottom - segment_height, x + bar_width, bottom), fill=mix(accent, hot, step / steps))
                peak_y = height - int(peak_level[index] * steps) * (segment_height + segment_gap) - 3
                draw.rectangle((x, max(0, peak_y), x + bar_width, max(0, peak_y) + 2), fill=peak)
            process.stdin.write(image.tobytes())
    finally:
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("foobar spectrum encoding failed")
    print(output)


if __name__ == "__main__":
    main()
