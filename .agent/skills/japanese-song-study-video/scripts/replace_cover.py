#!/usr/bin/env python3
"""Replace the frozen cover with a newly supplied 1:1 artwork revision.

The previous cover is archived inside source/ and both revisions are recorded in
source/source-manifest.json, so a user-requested cover change never destroys the
original evidence. The new file is normalised exactly like the freeze step
(RGB JPEG, quality 96, no chroma subsampling) to keep rendering deterministic.

Usage
    python replace_cover.py PROJECT_ROOT NEW_IMAGE [--reason TEXT] [--revision rNN]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,format_name:stream=index,codec_type,codec_name,width,height,bits_per_raw_sample,disposition",
         "-of", "json", str(path)],
        text=True, capture_output=True,
    )
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else {"probeError": result.stderr.strip()}


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
    parser.add_argument("new_image", type=Path)
    parser.add_argument("--reason", default="User supplied replacement artwork.")
    parser.add_argument("--revision")
    args = parser.parse_args()

    root = args.project_root.resolve()
    source = root / "source"
    target = source / "cover.jpg"
    manifest_path = source / "source-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing {manifest_path}; this project was not frozen with freeze_inputs.py")
    if not args.new_image.is_file():
        raise SystemExit(f"New artwork is missing: {args.new_image}")
    if not target.is_file():
        raise SystemExit("Current frozen cover is missing; refusing to guess")
    with Image.open(args.new_image) as image:
        if image.size[0] != image.size[1]:
            raise SystemExit(f"Cover must be 1:1 for the series layout, got {image.size}")
        source_size = image.size

    manifest = load(manifest_path)
    assets = manifest.get("assets", [])
    revision = args.revision or next_revision(assets)
    archive = source / f"cover-superseded-{revision}.jpg"
    previous_sha = sha(target)
    if archive.exists():
        if sha(archive) != previous_sha:
            raise SystemExit(f"Archive exists with different content for {revision}: {archive}")
    else:
        archive.write_bytes(target.read_bytes())
    # A frozen copy can carry the read-only attribute from the attachment store.
    target.chmod(target.stat().st_mode | stat.S_IWRITE)
    with Image.open(args.new_image) as image:
        image.convert("RGB").save(target, quality=96, subsampling=0)

    kept = [asset for asset in assets if asset.get("role") not in ("cover", "coverSuperseded", "coverCurrent")]
    kept.append({
        "role": "cover",
        "revision": revision,
        "originalAbsolutePath": str(args.new_image),
        "frozenAsset": "source/cover.jpg",
        "bytes": target.stat().st_size,
        "sha256": sha(target),
        "sourceDimensions": list(source_size),
        "probe": probe(target),
        "reason": args.reason,
        "replacedAt": datetime.now(timezone.utc).isoformat(),
    })
    kept.append({
        "role": "coverSuperseded",
        "revision": f"previous-of-{revision}",
        "frozenAsset": f"source/{archive.name}",
        "bytes": archive.stat().st_size,
        "sha256": previous_sha,
        "probe": probe(archive),
        "note": "Archived automatically by replace_cover.py; retained for audit.",
    })
    manifest["assets"] = kept
    manifest["coverRevision"] = revision
    write(manifest_path, manifest)

    note = (f"Cover revision {revision} installed from {args.new_image.name} "
            f"(sha256 {sha(target)}); previous cover archived as source/{archive.name} (sha256 {previous_sha}).")
    state_path = root / "project" / "build-state.json"
    if state_path.is_file():
        state = load(state_path)
        state.setdefault("notes", []).append(note)
        state.setdefault("unresolved", [])
        write(state_path, state)

    print(json.dumps({
        "installed": "source/cover.jpg", "revision": revision, "sha256": sha(target),
        "bytes": target.stat().st_size, "sourceDimensions": list(source_size),
        "archived": f"source/{archive.name}", "archivedSha256": previous_sha,
        "reminder": "Re-export the platform covers and regenerate previews; any existing render authorization is now stale.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
