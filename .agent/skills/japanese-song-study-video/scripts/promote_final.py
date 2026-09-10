#!/usr/bin/env python3
"""Promote only a QA-passed candidate into deliverables/final."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("qa_report", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve(); project = root / "project"
    args.candidate = args.candidate.resolve()
    args.qa_report = args.qa_report.resolve()
    qa = load(args.qa_report)
    candidate_hash = sha(args.candidate)
    if qa.get("result") != "passed" or qa.get("candidateSha256") != candidate_hash:
        raise SystemExit("QA report is not passed or does not hash the candidate")
    probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,bits_per_raw_sample", "-of", "json", str(args.candidate)], check=True, text=True, capture_output=True).stdout)
    audio = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
    manifest = load(project / "input-manifest.json"); music = root / manifest["music"]["asset"]
    music_codec = next((stream["codec_name"] for stream in json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", str(music)], check=True, text=True, capture_output=True).stdout)["streams"] if stream["codec_type"] == "audio"), None)
    if music_codec == "flac" and (not audio or audio.get("codec_name") != "flac" or args.candidate.suffix.lower() != ".mkv"):
        raise SystemExit("FLAC input must remain FLAC in an MKV candidate")
    destination = root / "deliverables" / "final" / args.candidate.name
    destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(args.candidate, destination)
    write(project / "final-manifest.json", {"schemaVersion": 2, "output": destination.relative_to(root).as_posix(), "outputSha256": candidate_hash, "qaReport": args.qa_report.relative_to(root).as_posix(), "probe": probe})
    state_path = project / "build-state.json"; state = load(state_path)
    state.update({"stage": "delivered", "renderAuthorization": True}); state.setdefault("notes", []).append(f"QA-passed candidate promoted: {destination.name}")
    write(state_path, state)
    print(json.dumps({"output": str(destination), "sha256": candidate_hash}, ensure_ascii=False))


if __name__ == "__main__":
    main()
