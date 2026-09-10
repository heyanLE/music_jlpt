"""Locate the same musical program in a FLAC and an MV audio track.

It compares normalized log-spectral feature windows, which rejects unrelated
spoken/ambient MV audio better than a leading-RMS onset detector.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
MUSIC = ROOT / "source" / "music.flac"
VIDEO = ROOT / "source" / "background.webm"
OUTPUT = ROOT / "project" / "qa" / "music-program-match.json"
RATE, WINDOW, HOP = 8_000, 2_048, 512


def audio(path: Path) -> np.ndarray:
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "pipe:1"]
    raw = subprocess.run(command, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768


def features(samples: np.ndarray) -> np.ndarray:
    count = 1 + (len(samples) - WINDOW) // HOP
    frames = np.lib.stride_tricks.sliding_window_view(samples, WINDOW)[::HOP][:count]
    frames = frames * np.hanning(WINDOW)
    spectrum = np.log1p(np.abs(np.fft.rfft(frames, axis=1)))
    # Stable, coarse bands reduce sensitivity to different mastering/codecs.
    bands = np.array_split(spectrum[:, 2:700], 32, axis=1)
    vector = np.stack([band.mean(axis=1) for band in bands], axis=1)
    vector -= vector.mean(axis=1, keepdims=True)
    vector /= np.maximum(np.linalg.norm(vector, axis=1, keepdims=True), 1e-9)
    return vector


def main() -> None:
    flac, mv = features(audio(MUSIC)), features(audio(VIDEO))
    # Several non-repeating phrases make the offset robust against a chorus.
    query_len = round(12 * RATE / HOP)
    matches = []
    for seconds in (8, 14, 20, 28):
        query_start = round(seconds * RATE / HOP)
        query = flac[query_start:query_start + query_len]
        scores = []
        for start in range(0, len(mv) - len(query)):
            scores.append(float((mv[start:start + len(query)] * query).sum(axis=1).mean()))
        best = int(np.argmax(scores)); second = float(np.partition(scores, -2)[-2])
        matches.append({"flacStartMs": round(query_start * HOP * 1000 / RATE), "mvStartMs": round(best * HOP * 1000 / RATE), "offsetMs": round((best - query_start) * HOP * 1000 / RATE), "score": scores[best], "margin": scores[best] - second})
    offsets = [match["offsetMs"] for match in matches]
    offset = round(float(np.median(offsets)))
    result = {
        "schemaVersion": 1,
        "algorithm": "normalized-log-spectral-window-v1",
        "sampleRate": RATE,
        "hopMs": HOP * 1000 / RATE,
        "queryDurationMs": round(query_len * HOP * 1000 / RATE),
        "matches": matches,
        "acceptedOffsetMs": offset,
        "offsetSpreadMs": max(offsets) - min(offsets),
        "interpretation": "mv time = flac time + offsetMs for the matched musical program"
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
