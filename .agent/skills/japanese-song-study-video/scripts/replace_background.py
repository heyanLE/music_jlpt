#!/usr/bin/env python3
"""Replace the frozen background video with a newly supplied one.

Mirrors replace_cover.py: the superseded file is archived inside `source/`, both
revisions are recorded in `source/source-manifest.json`, and the project state gets
a note. Re-running `configure_layers.py` afterwards is mandatory when the preset
derives its schedule from the video length (the hybrid hand-off is the video
duration), and any existing render authorization becomes stale.

Usage
    python replace_background.py PROJECT_ROOT NEW_VIDEO [--reason TEXT] [--revision rNN]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_writable(path: Path) -> None:
    """Attachment copies can carry the read-only attribute; clear it before overwriting."""
    if path.exists():
        path.chmod(path.stat().st_mode | stat.S_IWRITE | stat.S_IREAD)


def probe(path: Path) -> dict:
    return json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,format_name:stream=index,codec_type,codec_name,width,height,r_frame_rate,sample_rate",
         "-of", "json", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout)


def duration_seconds(path: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout.strip())


def next_revision(assets: list[dict]) -> str:
    highest = 0
    for asset in assets:
        revision = str(asset.get("revision", ""))
        if revision.startswith("r") and revision[1:].isdigit():
            highest = max(highest, int(revision[1:]))
    return f"r{highest + 1:02d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("new_video", type=Path)
    parser.add_argument("--reason", default="User supplied a replacement background video.")
    parser.add_argument("--revision")
    parser.add_argument("--role", default="background")
    args = parser.parse_args()

    root = args.project_root.resolve()
    source = root / "source"
    manifest_path = source / "source-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing {manifest_path}; this project was not created by freeze_inputs.py")
    if not args.new_video.is_file():
        raise SystemExit(f"New video is missing: {args.new_video}")
    probe_path = probe(args.new_video)
    video_stream = next((stream for stream in probe_path["streams"] if stream["codec_type"] == "video"), None)
    if video_stream is None:
        raise SystemExit("The replacement must contain a video stream")

    manifest = load(manifest_path)
    assets = manifest.get("assets", [])
    existing = next((asset for asset in assets if asset.get("role") == args.role and asset.get("frozenAsset", "").startswith("source/")), None)
    if existing is None:
        raise SystemExit(f"No frozen {args.role} asset to replace")
    target = root / existing["frozenAsset"]
    revision = args.revision or next_revision(assets)
    archive = source / f"{args.role}-superseded-{revision}{target.suffix}"
    previous_sha = sha(target)
    if archive.exists():
        # A previous run may have archived the file before failing later; only reuse
        # the archive when it really holds the current revision's predecessor.
        if sha(archive) != previous_sha:
            raise SystemExit(f"Archive exists with different content for {revision}: {archive}")
    else:
        make_writable(archive)
        shutil.copy2(target, archive)
        archive.chmod(archive.stat().st_mode & ~stat.S_IWRITE)
    make_writable(target)
    shutil.copy2(args.new_video, target)
    make_writable(target)
    target.chmod(target.stat().st_mode & ~stat.S_IWRITE)

    # The previous role entry describes a file whose content just changed, so it must
    # not stay in the manifest as if it still matched; the archive entry keeps the
    # superseded revision and its hash.
    assets = [asset for asset in assets
              if not (asset.get("role") == args.role and asset.get("frozenAsset") == existing["frozenAsset"])
              and not (asset.get("role") == f"{args.role}Superseded" and asset.get("revision") == revision)]
    assets.append({
        "role": args.role,
        "revision": revision,
        "originalAbsolutePath": str(args.new_video),
        "frozenAsset": existing["frozenAsset"],
        "bytes": target.stat().st_size,
        "sha256": sha(target),
        "probe": probe(target),
        "reason": args.reason,
        "replacedAt": datetime.now(timezone.utc).isoformat(),
    })
    assets.append({
        "role": f"{args.role}Superseded",
        "revision": revision,
        "frozenAsset": f"source/{archive.name}",
        "bytes": archive.stat().st_size,
        "sha256": previous_sha,
        "probe": probe(archive),
        "note": "Archived automatically by replace_background.py; retained for audit.",
    })
    manifest["assets"] = assets
    manifest[f"{args.role}Revision"] = revision
    write(manifest_path, manifest)

    state_path = root / "project" / "build-state.json"
    if state_path.is_file():
        state = load(state_path)
        state.setdefault("notes", []).append(
            f"Background revision {revision} installed from {args.new_video.name} (sha256 {sha(target)}, "
            f"{duration_seconds(target):.3f} s); previous video archived as source/{archive.name} (sha256 {previous_sha})."
        )
        write(state_path, state)

    print(json.dumps({
        "installed": existing["frozenAsset"],
        "revision": revision,
        "sha256": sha(target),
        "durationSeconds": round(duration_seconds(target), 3),
        "resolution": f"{video_stream.get('width')}x{video_stream.get('height')}",
        "frameRate": video_stream.get("r_frame_rate"),
        "archived": f"source/{archive.name}",
        "reminder": "Re-run configure_layers.py (the hybrid hand-off equals the video length), re-measure alignment, "
                    "refresh previews and re-authorize before any render.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
