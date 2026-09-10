#!/usr/bin/env python3
"""Replace a mistakenly derived cover with the frozen music file's artwork."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from freeze_inputs import extract_embedded_cover, probe


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    manifest_path = root / "project" / "input-manifest.json"
    source_manifest_path = root / "source" / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    music = root / manifest["music"]["asset"]
    cover = root / manifest["cover"]["asset"]
    if not extract_embedded_cover(music, cover):
        raise SystemExit("The frozen music source has no extractable attached artwork")

    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    for entry in source_manifest.get("assets", []):
        if entry.get("role") == "cover":
            entry.update({
                "originalAbsolutePath": str(music),
                "frozenAsset": cover.relative_to(root).as_posix(),
                "bytes": cover.stat().st_size,
                "sha256": sha(cover),
                "probe": probe(cover),
                "origin": "embedded-attached-picture-from-frozen-music",
            })
            break
    else:
        raise SystemExit("source manifest has no cover entry")
    source_manifest_path.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"cover": str(cover), "sha256": sha(cover), "bytes": cover.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
