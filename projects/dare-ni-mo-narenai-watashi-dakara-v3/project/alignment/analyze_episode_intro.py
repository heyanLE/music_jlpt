#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal


def load_stereo(path: Path) -> tuple[np.ndarray, int]:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    return audio[:, :2], sample_rate


def band_features(audio: np.ndarray, sample_rate: int, channel: str) -> tuple[np.ndarray, float]:
    if channel == "side":
        mono = audio[:, 0] - audio[:, 1]
    elif channel == "mid":
        mono = 0.5 * (audio[:, 0] + audio[:, 1])
    else:
        mono = audio[:, 0]
    mono = signal.sosfiltfilt(signal.butter(4, [80, 7000], btype="bandpass", fs=sample_rate, output="sos"), mono)
    nperseg = 1024
    hop = 160
    frequencies, _, spectrum = signal.stft(
        mono,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=nperseg - hop,
        boundary=None,
        padded=False,
    )
    power = np.abs(spectrum) ** 2
    edges = np.geomspace(80, 7000, 25)
    bands = []
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (frequencies >= low) & (frequencies < high)
        bands.append(np.log1p(power[mask].mean(axis=0) * 10000.0))
    features = np.stack(bands, axis=1)
    features -= np.median(features, axis=0, keepdims=True)
    scale = np.std(features, axis=0, keepdims=True)
    features /= np.maximum(scale, 1e-6)
    return features, hop / sample_rate


def scan_offsets(episode: np.ndarray, master: np.ndarray, seconds_per_frame: float, max_master_seconds: float) -> list[dict]:
    master_frames = min(len(master), int(max_master_seconds / seconds_per_frame))
    reference = master[:master_frames]
    if len(episode) < len(reference):
        raise ValueError("episode analysis window is shorter than the master reference")
    score = np.zeros(len(episode) - len(reference) + 1, dtype=np.float64)
    for band in range(reference.shape[1]):
        score += signal.correlate(episode[:, band], reference[:, band], mode="valid", method="fft")
    score /= reference.shape[0] * reference.shape[1]
    peaks, _ = signal.find_peaks(score, distance=max(1, int(0.5 / seconds_per_frame)))
    ranked = peaks[np.argsort(score[peaks])[::-1]] if len(peaks) else np.array([int(np.argmax(score))])
    return [
        {
            "offsetSecondsWithinEpisodeWindow": round(float(index * seconds_per_frame), 4),
            "score": round(float(score[index]), 6),
        }
        for index in ranked[:10]
    ]


def filtered_channel(audio: np.ndarray, sample_rate: int, channel: str) -> np.ndarray:
    if channel == "side":
        mono = audio[:, 0] - audio[:, 1]
    elif channel == "mid":
        mono = 0.5 * (audio[:, 0] + audio[:, 1])
    else:
        mono = audio[:, 0]
    mono = signal.sosfiltfilt(signal.butter(4, [100, 7000], btype="bandpass", fs=sample_rate, output="sos"), mono)
    mono -= np.mean(mono)
    return mono


def fine_waveform_match(
    episode: np.ndarray,
    master: np.ndarray,
    sample_rate: int,
    channel: str,
    coarse_offset_seconds: float,
    master_start_seconds: float,
    duration_seconds: float,
    search_radius_seconds: float = 0.75,
) -> dict:
    episode_mono = filtered_channel(episode, sample_rate, channel)
    master_mono = filtered_channel(master, sample_rate, channel)
    master_start = round(master_start_seconds * sample_rate)
    duration = round(duration_seconds * sample_rate)
    reference = master_mono[master_start : master_start + duration]
    expected = (coarse_offset_seconds + master_start_seconds) * sample_rate
    candidate_start = max(0, round(expected - search_radius_seconds * sample_rate))
    candidate_end = min(len(episode_mono), round(expected + duration + search_radius_seconds * sample_rate))
    candidate = episode_mono[candidate_start:candidate_end]
    correlation = signal.correlate(candidate, reference, mode="valid", method="fft")
    reference_energy = float(np.sum(reference * reference))
    window_energy = np.convolve(candidate * candidate, np.ones(len(reference), dtype=np.float32), mode="valid")
    normalized = correlation / np.sqrt(np.maximum(window_energy * reference_energy, 1e-12))
    peak = int(np.argmax(normalized))
    episode_reference_start = (candidate_start + peak) / sample_rate
    return {
        "channel": channel,
        "masterStartSeconds": master_start_seconds,
        "durationSeconds": duration_seconds,
        "offsetSecondsWithinEpisodeWindow": round(episode_reference_start - master_start_seconds, 6),
        "normalizedCorrelation": round(float(normalized[peak]), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_wav", type=Path)
    parser.add_argument("master_wav", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--episode-window-start", type=float, required=True)
    parser.add_argument("--reference-seconds", type=float, default=60.0)
    args = parser.parse_args()

    episode, episode_rate = load_stereo(args.episode_wav)
    master, master_rate = load_stereo(args.master_wav)
    if episode_rate != master_rate:
        raise ValueError(f"sample-rate mismatch: {episode_rate} != {master_rate}")

    results = {}
    for channel in ("side", "mid", "left"):
        episode_features, frame_seconds = band_features(episode, episode_rate, channel)
        master_features, master_frame_seconds = band_features(master, master_rate, channel)
        if abs(frame_seconds - master_frame_seconds) > 1e-9:
            raise ValueError("feature hop mismatch")
        peaks = scan_offsets(episode_features, master_features, frame_seconds, args.reference_seconds)
        for peak in peaks:
            peak["episodeAbsoluteSecondsForMusicZero"] = round(
                args.episode_window_start + peak["offsetSecondsWithinEpisodeWindow"], 4
            )
        results[channel] = peaks

    coarse_offset = results["side"][0]["offsetSecondsWithinEpisodeWindow"]
    fine = []
    for channel in ("side", "mid", "left"):
        for master_start, duration in ((15.0, 20.0), (45.0, 20.0), (70.0, 15.0)):
            fine.append(
                fine_waveform_match(
                    episode,
                    master,
                    episode_rate,
                    channel,
                    coarse_offset,
                    master_start,
                    duration,
                )
            )
    reliable = [item for item in fine if item["normalizedCorrelation"] >= 0.2]
    refined_offset = float(np.median([item["offsetSecondsWithinEpisodeWindow"] for item in reliable])) if reliable else coarse_offset

    report = {
        "schemaVersion": 1,
        "episodeWindowStartSeconds": args.episode_window_start,
        "referenceSeconds": args.reference_seconds,
        "sampleRate": episode_rate,
        "featureHopSeconds": frame_seconds,
        "results": results,
        "fineWaveformMatches": fine,
        "refined": {
            "reliableThreshold": 0.2,
            "reliableMatchCount": len(reliable),
            "offsetSecondsWithinEpisodeWindow": round(refined_offset, 6),
            "episodeAbsoluteSecondsForMusicZero": round(args.episode_window_start + refined_offset, 6),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
