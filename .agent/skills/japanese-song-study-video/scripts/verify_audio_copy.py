#!/usr/bin/env python3
"""Prove the delivered candidate's audio was preserved, not re-encoded.

Two levels:
  * stream level - the candidate's audio codec/sample rate/bit depth must match the
    frozen source, and a FLAC source must stay FLAC inside Matroska;
  * sample level - the decoded PCM of both must be byte-identical. Use --seconds for
    a fast pre-render probe; the default compares the whole programme.

Usage
    python verify_audio_copy.py PROJECT_ROOT CANDIDATE [--seconds N] [--out REPORT] [--expect-codec flac]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def probe_audio(path: Path) -> dict:
    document = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate,channels,bits_per_raw_sample,start_time,duration",
         "-of", "json", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout)
    streams = document.get("streams", [])
    if not streams:
        raise SystemExit(f"No audio stream in {path}")
    return streams[0]


def pcm(path: Path, seconds: float | None) -> bytes:
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-vn"]
    if seconds:
        command += ["-t", f"{seconds:.6f}"]
    command += ["-f", "s16le", "-acodec", "pcm_s16le", "-"]
    return subprocess.run(command, check=True, stdout=subprocess.PIPE).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--seconds", type=float, help="Compare only the first N seconds (fast pre-render probe)")
    parser.add_argument("--expect-codec")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    root = args.project_root.resolve()
    candidate = args.candidate.resolve()
    manifest = load(root / "project" / "input-manifest.json")
    music = root / manifest["music"]["asset"]
    source, produced = probe_audio(music), probe_audio(candidate)
    expected_codec = args.expect_codec or source["codec_name"]

    problems: list[str] = []
    for field in ("codec_name", "sample_rate", "channels", "bits_per_raw_sample"):
        if source.get(field) != produced.get(field):
            problems.append(f"audio {field} changed: source {source.get(field)!r} -> candidate {produced.get(field)!r}")
    if produced["codec_name"] != expected_codec:
        problems.append(f"candidate audio codec is {produced['codec_name']!r}, expected {expected_codec!r}")
    if source["codec_name"] == "flac" and candidate.suffix.lower() != ".mkv":
        problems.append("a FLAC source must be delivered in an MKV container")

    seconds = args.seconds
    if seconds is None:
        seconds = round(float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(candidate)],
            check=True, text=True, capture_output=True,
        ).stdout.strip()), 3)
    source_pcm, candidate_pcm = pcm(music, seconds), pcm(candidate, seconds)
    bit_exact = source_pcm == candidate_pcm
    if not bit_exact and len(source_pcm) == len(candidate_pcm):
        differing = sum(1 for index in range(0, len(source_pcm), 2)
                        if source_pcm[index:index + 2] != candidate_pcm[index:index + 2])
        problems.append(f"decoded PCM differs in {differing} of {len(source_pcm) // 2} samples")

    report = {
        "schemaVersion": 1,
        "project": root.name,
        "requirement": "audio must not be re-encoded",
        "candidate": str(candidate.relative_to(root)).replace("\\", "/") if candidate.is_relative_to(root) else str(candidate),
        "source": str(music.relative_to(root)).replace("\\", "/"),
        "comparedSeconds": seconds,
        "sourceStream": source,
        "candidateStream": produced,
        "sourcePcmBytes": len(source_pcm),
        "candidatePcmBytes": len(candidate_pcm),
        "sourcePcmSha256": sha(source_pcm),
        "candidatePcmSha256": sha(candidate_pcm),
        "bitExact": bit_exact,
        "result": "passed" if bit_exact and not problems else "failed",
        "problems": problems,
    }
    output = args.out or root / "project" / "qa" / ("audio-preservation-candidate.json" if args.seconds is None else "audio-preservation-probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: report[key] for key in ("result", "bitExact", "comparedSeconds", "candidateStream", "problems")},
                     ensure_ascii=False, indent=2))
    if report["result"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
