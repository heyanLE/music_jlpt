#!/usr/bin/env python3
"""Freeze project inputs not supported by the single-background bootstrapper."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECOND_VIDEO = Path(r"C:\Users\eke_l\Videos\TubeGet\yonige「芽吹くとき」 official music video.mp4")
COVER_SOURCE = Path(r"C:\Users\eke_l\Music\鈴代紗弓 - 感情グラス.flac")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,format_name:stream=index,codec_type,codec_name,width,height,sample_rate,bits_per_raw_sample,disposition",
        "-of", "json", str(path),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def freeze(role: str, original: Path, frozen_name: str, entries: list[dict]) -> str:
    target = ROOT / "source" / frozen_name
    if target.exists():
        raise SystemExit(f"Frozen target already exists: {target}")
    shutil.copy2(original, target)
    entries.append({
        "role": role,
        "originalAbsolutePath": str(original.resolve()),
        "frozenAsset": target.relative_to(ROOT).as_posix(),
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
        "probe": probe(target),
    })
    return target.relative_to(ROOT).as_posix()


def main() -> None:
    source_manifest_path = ROOT / "source" / "source-manifest.json"
    input_manifest_path = ROOT / "project" / "input-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    entries = source_manifest["assets"]
    second_asset = freeze("backgroundSecond", SECOND_VIDEO, "background-2.mp4", entries)
    cover_source_asset = freeze("coverSourceMedia", COVER_SOURCE, "cover-source-media.flac", entries)
    input_manifest["backgroundAssets"] = [
        {"id": "anime-opening", "asset": input_manifest["backgroundAsset"], "order": 1},
        {"id": "official-mv", "asset": second_asset, "order": 2},
    ]
    input_manifest["cover"]["origin"] = "embedded-art-from-separately-frozen-media"
    input_manifest["cover"]["sourceMedia"] = cover_source_asset
    input_manifest["cover"]["sourceTitle"] = "感情グラス"
    input_manifest["cover"]["sourceArtist"] = "上伊那ぼたん（CV.鈴代紗弓）"
    write_json(source_manifest_path, source_manifest)
    write_json(input_manifest_path, input_manifest)
    print(json.dumps({"backgroundSecond": second_asset, "coverSourceMedia": cover_source_asset}, ensure_ascii=False))


if __name__ == "__main__":
    main()
