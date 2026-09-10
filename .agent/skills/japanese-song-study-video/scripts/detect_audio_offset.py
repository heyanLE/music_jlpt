#!/usr/bin/env python3
"""Propose a signed music offset from leading audio onsets.

The report is advisory. configure_layers.py must explicitly accept it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


SR = 16000
WINDOW_MS = 50


def decode(path: Path) -> np.ndarray:
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-t", "30", "-f", "f32le", "-"]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode or not result.stdout:
        raise RuntimeError(result.stderr.decode("utf-8", "replace") or "no audio stream")
    return np.frombuffer(result.stdout, dtype=np.float32)


def onset(samples: np.ndarray) -> dict:
    size = SR * WINDOW_MS // 1000
    count = len(samples) // size
    if count < 8:
        raise RuntimeError("audio is too short for onset analysis")
    frames = samples[:count * size].reshape(count, size)
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    noise_floor = float(np.percentile(db, 15))
    peak = float(np.percentile(db, 98))
    # A file may begin with music and contain no leading noise-floor window.
    # Cap the threshold below the track peak so "onset at zero" remains valid.
    threshold = min(peak - 6.0, max(-45.0, noise_floor + 12.0))
    active = db >= threshold
    index = None
    for i in range(max(0, len(active) - 3)):
        if int(active[i:i + 4].sum()) >= 3:
            index = i
            break
    if index is None:
        raise RuntimeError(f"no stable onset above {threshold:.1f} dBFS")
    margin = peak - threshold
    confidence = "high" if margin >= 18 else "medium" if margin >= 6 else "low"
    return {
        "onsetMs": index * WINDOW_MS,
        "noiseFloorDb": round(noise_floor, 2),
        "thresholdDb": round(threshold, 2),
        "peakDb": round(peak, 2),
        "marginDb": round(margin, 2),
        "confidence": confidence,
    }


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("music", type=Path)
    parser.add_argument("background", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--max-absolute-offset-ms", type=int, default=10000)
    args = parser.parse_args()
    report: dict = {"schemaVersion": 1, "algorithm": "leading-rms-onset-v1", "windowMs": WINDOW_MS}
    try:
        music = onset(decode(args.music)); background = onset(decode(args.background))
        proposed = int(background["onsetMs"] - music["onsetMs"])
        confidence = "low" if "low" in (music["confidence"], background["confidence"]) else (
            "medium" if "medium" in (music["confidence"], background["confidence"]) else "high"
        )
        usable = abs(proposed) <= args.max_absolute_offset_ms and confidence in ("medium", "high")
        report.update({
            "result": "usable" if usable else "manual-review-required",
            "music": music, "background": background, "proposedOffsetMs": proposed,
            "definition": "backgroundOnsetMs - musicOnsetMs", "confidence": confidence,
            "guard": {"maxAbsoluteOffsetMs": args.max_absolute_offset_ms, "passed": abs(proposed) <= args.max_absolute_offset_ms},
            "warning": "Onset alignment is valid only when both streams contain the same musical program." if usable else "Use manual or zero offset.",
        })
    except Exception as error:
        report.update({"result": "unusable", "confidence": "low", "error": str(error)})
    write(args.report, report)
    print(json.dumps(report, ensure_ascii=False))
    if report["result"] == "unusable":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
