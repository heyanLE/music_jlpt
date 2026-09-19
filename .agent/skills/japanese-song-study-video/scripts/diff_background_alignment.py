#!/usr/bin/env python3
"""Diff a reference music file against a video's background audio.

Estimates the signed relationship "video time = music time + offset" from several
independent windows instead of trusting a single correlation peak. The result is
evidence for the alignment decision, never an automatically applied offset.

Usage
    python diff_background_alignment.py MUSIC BACKGROUND REPORT
        [--sample-rate 3000] [--window-seconds 6] [--step-seconds 5]
        [--start-seconds 2] [--end-seconds N] [--min-score 0.45]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

try:  # FFT correlation keeps a 90 s vs 6 s comparison fast
    from scipy.signal import correlate as _correlate

    def correlate(reference: np.ndarray, template: np.ndarray) -> np.ndarray:
        return _correlate(reference, template, mode="valid", method="fft")
except ImportError:  # pragma: no cover - fallback for hosts without scipy
    def correlate(reference: np.ndarray, template: np.ndarray) -> np.ndarray:
        size = 1 << (len(reference) + len(template) - 1).bit_length()
        spectrum = np.fft.rfft(reference, size) * np.conj(np.fft.rfft(template, size))
        return np.fft.irfft(spectrum, size)[len(template) - 1:len(reference)]


MIN_STRONG_SCORE = 0.45
CONSISTENCY_TOLERANCE_SECONDS = 0.08


def decode(path: Path, sample_rate: int) -> np.ndarray:
    """Band-limited mono PCM; the band keeps music-to-music matching robust."""
    command = [
        "ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
        "-ar", str(sample_rate), "-af", "highpass=f=90,lowpass=f=1800",
        "-f", "f32le", "-",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode or not result.stdout:
        raise SystemExit(result.stderr.decode("utf-8", "replace") or "audio decode failed")
    audio = np.frombuffer(result.stdout, dtype=np.float32).astype(np.float64)
    audio -= np.mean(audio)
    peak = np.max(np.abs(audio))
    return audio / peak if peak else audio


def normalized_match(reference: np.ndarray, template: np.ndarray) -> tuple[int, float]:
    """Index and score of the best normalized cross-correlation position."""
    template = template - np.mean(template)
    template_energy = float(np.dot(template, template))
    if template_energy <= 1e-12:
        return 0, 0.0
    window = len(template)
    numerator = correlate(reference, template)
    squared = reference * reference
    cumulative = np.concatenate(([0.0], np.cumsum(squared)))
    energy = cumulative[window:] - cumulative[:-window]
    scores = numerator / np.sqrt(np.maximum(energy * template_energy, 1e-12))
    index = int(np.argmax(scores))
    return index, float(scores[index])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music", type=Path)
    parser.add_argument("background", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--sample-rate", type=int, default=3000)
    parser.add_argument("--window-seconds", type=float, default=6.0)
    parser.add_argument("--step-seconds", type=float, default=5.0)
    parser.add_argument("--start-seconds", type=float, default=2.0)
    parser.add_argument("--end-seconds", type=float)
    parser.add_argument("--min-score", type=float, default=MIN_STRONG_SCORE)
    args = parser.parse_args()

    music = decode(args.music, args.sample_rate)
    video = decode(args.background, args.sample_rate)
    video_duration = len(video) / args.sample_rate
    window = round(args.window_seconds * args.sample_rate)
    end = min(video_duration - args.window_seconds, args.end_seconds or video_duration)

    rows, position = [], args.start_seconds
    while position <= end:
        start_sample = round(position * args.sample_rate)
        template = video[start_sample:start_sample + window]
        rms = float(np.sqrt(np.mean(template * template)))
        if len(template) == window and rms >= 0.002:
            match_sample, score = normalized_match(music, template)
            music_start = match_sample / args.sample_rate
            rows.append({
                "videoStartSeconds": round(position, 3),
                "musicStartSeconds": round(music_start, 3),
                "videoMinusMusicSeconds": round(position - music_start, 3),
                "score": round(score, 5),
                "windowRms": round(rms, 6),
            })
        position += args.step_seconds

    strong = [row for row in rows if row["score"] >= args.min_score]
    offsets = np.array([row["videoMinusMusicSeconds"] for row in strong], dtype=float)
    median = float(np.median(offsets)) if len(offsets) else None
    consistent = int(np.sum(np.abs(offsets - median) <= CONSISTENCY_TOLERANCE_SECONDS)) if median is not None else 0
    linear = bool(len(strong) >= 3 and consistent / len(strong) >= 0.7)
    document = {
        "schemaVersion": 1,
        "algorithm": "multi-window-normalized-waveform-correlation-v1",
        "music": str(args.music).replace("\\", "/"),
        "background": str(args.background).replace("\\", "/"),
        "sampleRate": args.sample_rate,
        "windowSeconds": args.window_seconds,
        "videoDurationSeconds": round(video_duration, 6),
        "matches": rows,
        "summary": {
            "strongMatchCount": len(strong),
            "medianVideoMinusMusicSeconds": round(median, 3) if median is not None else None,
            "consistentWithin80msCount": consistent,
            "linearAlignmentLikely": linear,
            "notes": [
                "video time = music time + medianVideoMinusMusicSeconds for the strong windows",
                "a piecewise result (two distinct clusters) means the video is an edit, not a single excerpt",
                "this is evidence only: apply an offset with configure_layers.py and record the reason",
            ],
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(args.report).replace("\\", "/"), **document["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
