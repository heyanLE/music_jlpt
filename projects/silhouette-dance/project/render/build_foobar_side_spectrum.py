"""Render a classic segmented Foobar2000-style spectrum for side placement."""
import argparse
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

FPS = 24000 / 1001
SAMPLE_RATE, BARS, FFT_SIZE = 8000, 40, 2048
WIDTH, HEIGHT = 650, 70


def mix(a, b, amount):
    return tuple(round(a[i] * (1 - amount) + b[i] * amount) for i in range(3))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    work, output = Path(args.work), Path(args.output)
    work.mkdir(parents=True, exist_ok=True)
    pcm = work / "foobar-side-mono-8k.f32le"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", args.audio, "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", str(pcm)], check=True)
    samples = np.fromfile(pcm, dtype=np.float32)
    frames = math.ceil(len(samples) / SAMPLE_RATE * FPS)
    window = np.hanning(FFT_SIZE)
    edges = np.geomspace(2, FFT_SIZE // 2, BARS + 1).astype(int)
    level, peak = np.zeros(BARS), np.zeros(BARS)
    accent, hot, peak_color = (32, 96, 224), (36, 109, 255), (152, 191, 255)
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", "24000/1001", "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "24000/1001", "-fps_mode", "cfr", str(output)
    ], stdin=subprocess.PIPE)
    gap, segment_height, segment_gap = 5, 4, 2
    bar_width = (WIDTH - gap * (BARS - 1)) // BARS
    steps = max(1, HEIGHT // (segment_height + segment_gap) - 1)
    try:
        for frame in range(frames):
            center = int(frame / FPS * SAMPLE_RATE)
            raw = np.zeros(FFT_SIZE, dtype=np.float32)
            start, end = max(0, center - FFT_SIZE // 2), min(len(samples), center + FFT_SIZE // 2)
            offset = start - (center - FFT_SIZE // 2)
            raw[offset:offset + end - start] = samples[start:end]
            magnitude = np.abs(np.fft.rfft(raw * window))
            bands = np.array([magnitude[edges[i]:max(edges[i] + 1, edges[i + 1])].mean() for i in range(BARS)])
            target = np.clip(np.log1p(bands * 42) / 5.0, 0.02, 1.0)
            level = np.where(target > level, level + (target - level) * 0.70, level + (target - level) * 0.18)
            peak = np.maximum(peak - 0.018, level)
            image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            draw = ImageDraw.Draw(image)
            for index, value in enumerate(level):
                x = index * (bar_width + gap)
                count = max(1, int(1 + value * steps))
                for step in range(count):
                    bottom = HEIGHT - 1 - step * (segment_height + segment_gap)
                    draw.rectangle((x, bottom - segment_height, x + bar_width, bottom), fill=mix(accent, hot, step / steps))
                peak_y = HEIGHT - int(peak[index] * steps) * (segment_height + segment_gap) - 3
                draw.rectangle((x, max(0, peak_y), x + bar_width, max(0, peak_y) + 2), fill=peak_color)
            proc.stdin.write(image.tobytes())
    finally:
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("Foobar side spectrum encoding failed")


if __name__ == "__main__":
    main()
