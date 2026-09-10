#!/usr/bin/env python3
"""Compare a reference music file with a video's audio at multiple windows."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import correlate


def decode(path: Path, sample_rate: int) -> np.ndarray:
    command = [
        "ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
        "-ar", str(sample_rate), "-af", "highpass=f=90,lowpass=f=1800",
        "-f", "f32le", "-",
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode or not result.stdout:
        raise RuntimeError(result.stderr.decode("utf-8", "replace") or "audio decode failed")
    audio = np.frombuffer(result.stdout, dtype=np.float32).astype(np.float64)
    audio -= np.mean(audio)
    peak = np.max(np.abs(audio))
    return audio / peak if peak else audio


def normalized_match(reference: np.ndarray, template: np.ndarray) -> tuple[int, float]:
    template = template - np.mean(template)
    template_energy = float(np.dot(template, template))
    if template_energy <= 1e-12:
        return 0, 0.0
    numerator = correlate(reference, template, mode="valid", method="fft")
    squared = reference * reference
    cumulative = np.concatenate(([0.0], np.cumsum(squared)))
    energy = cumulative[len(template):] - cumulative[:-len(template)]
    denominator = np.sqrt(np.maximum(energy * template_energy, 1e-12))
    scores = numerator / denominator
    index = int(np.argmax(scores))
    return index, float(scores[index])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music", type=Path)
    parser.add_argument("video", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--sample-rate", type=int, default=2000)
    parser.add_argument("--window-seconds", type=float, default=8.0)
    parser.add_argument("--step-seconds", type=float, default=10.0)
    parser.add_argument("--start-seconds", type=float, default=6.0)
    parser.add_argument("--end-seconds", type=float)
    args = parser.parse_args()

    music = decode(args.music, args.sample_rate)
    video = decode(args.video, args.sample_rate)
    video_duration = len(video) / args.sample_rate
    end = min(video_duration - args.window_seconds, args.end_seconds or video_duration)
    window_samples = round(args.window_seconds * args.sample_rate)
    rows = []
    position = args.start_seconds
    while position <= end:
        start_sample = round(position * args.sample_rate)
        template = video[start_sample:start_sample + window_samples]
        rms = float(np.sqrt(np.mean(template * template)))
        if len(template) == window_samples and rms >= 0.002:
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

    strong = [row for row in rows if row["score"] >= 0.45]
    offsets = np.array([row["videoMinusMusicSeconds"] for row in strong], dtype=float)
    median_offset = float(np.median(offsets)) if len(offsets) else None
    deviations = np.abs(offsets - median_offset) if median_offset is not None else np.array([])
    consistent = int(np.sum(deviations <= 0.08)) if len(deviations) else 0
    report = {
        "schemaVersion": 1,
        "algorithm": "multi-window-normalized-waveform-correlation-v1",
        "sampleRate": args.sample_rate,
        "windowSeconds": args.window_seconds,
        "videoDurationSeconds": round(video_duration, 6),
        "matches": rows,
        "summary": {
            "strongMatchCount": len(strong),
            "medianVideoMinusMusicSeconds": round(median_offset, 3) if median_offset is not None else None,
            "consistentWithin80msCount": consistent,
            "linearAlignmentLikely": bool(len(strong) >= 3 and consistent / len(strong) >= 0.7),
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
