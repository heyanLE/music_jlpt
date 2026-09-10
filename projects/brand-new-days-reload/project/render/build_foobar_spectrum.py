"""Build a transparent-keyed foobar-style real-time spectrum for Brand New Days."""
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parents[2]
# The frozen FLAC has a recoverable damaged frame. Use the already QA-passed
# AAC delivery track solely for deterministic spectrum analysis.
AUDIO = PROJECT / "deliverables" / "final" / "brand-new-days-reload--intro-fade-spectrum-continuous--glass-stems--20260816-r07.mp4"
WORK = PROJECT / "project" / "work" / "20260816-r08-foobar-spectrum"
PCM = WORK / "mono-8k.f32le"
OUTPUT = PROJECT / "project" / "foobar-classic-spectrum-v1.mp4"
FPS, SAMPLE_RATE, WIDTH, HEIGHT = 30, 8000, 1848, 150
BARS, FFT_SIZE = 84, 2048
ACCENT, HOT, PEAK = (166, 15, 42), (235, 45, 76), (255, 151, 169)

def blend(a, b, amount):
    return tuple(round(a[i] * (1 - amount) + b[i] * amount) for i in range(3))

WORK.mkdir(parents=True, exist_ok=True)
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(AUDIO), "-ac", "1", "-ar",
    str(SAMPLE_RATE), "-f", "f32le", str(PCM)
], check=True)
samples = np.fromfile(PCM, dtype=np.float32)
duration = len(samples) / SAMPLE_RATE
frame_count = math.ceil(duration * FPS)
window = np.hanning(FFT_SIZE)
edges = np.geomspace(2, FFT_SIZE // 2, BARS + 1).astype(int)
level = np.zeros(BARS)
peak = np.zeros(BARS)

process = subprocess.Popen([
    "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an", "-c:v",
    "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
    "-fps_mode", "cfr", str(OUTPUT)
], stdin=subprocess.PIPE)

gap = 7
bar_width = (WIDTH - gap * (BARS - 1)) // BARS
segment_height, segment_gap = 5, 2
try:
    for frame in range(frame_count):
        center = int(frame / FPS * SAMPLE_RATE)
        raw = np.zeros(FFT_SIZE, dtype=np.float32)
        start = max(0, center - FFT_SIZE // 2)
        end = min(len(samples), center + FFT_SIZE // 2)
        offset = start - (center - FFT_SIZE // 2)
        raw[offset:offset + end - start] = samples[start:end]
        magnitude = np.abs(np.fft.rfft(raw * window))
        bands = np.array([
            magnitude[edges[i]:max(edges[i] + 1, edges[i + 1])].mean()
            for i in range(BARS)
        ])
        target = np.clip(np.log1p(bands * 42) / 5.0, 0, 1)
        level = np.where(target > level, level + (target - level) * 0.70,
                         level + (target - level) * 0.18)
        peak = np.maximum(peak - 0.018, level)

        image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        for index, value in enumerate(level):
            x = index * (bar_width + gap)
            count = max(1, int(1 + value * 18))
            for step in range(count):
                bottom = HEIGHT - step * (segment_height + segment_gap)
                top = bottom - segment_height
                color = blend(ACCENT, HOT, step / 18)
                draw.rectangle((x, top, x + bar_width, bottom), fill=color)
            peak_y = HEIGHT - int(peak[index] * 18) * (segment_height + segment_gap) - 5
            draw.rectangle((x, peak_y, x + bar_width, peak_y + 3), fill=PEAK)
        process.stdin.write(image.tobytes())
finally:
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("foobar spectrum encoding failed")

print(OUTPUT)
