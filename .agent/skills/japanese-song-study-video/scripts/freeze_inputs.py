#!/usr/bin/env python3
"""Create a project workspace and freeze role-named source assets once."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name:stream=index,codec_type,codec_name,width,height,sample_rate,bits_per_raw_sample,disposition", "-of", "json", str(path)], text=True, capture_output=True)
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else {"probeError": result.stderr.strip()}


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def copy_once(source: Path, target: Path) -> None:
    if target.exists(): raise SystemExit(f"Frozen target already exists: {target}")
    shutil.copy2(source, target)


def extract_embedded_cover(media: Path, target: Path) -> bool:
    """Extract an attached picture using its ffprobe stream index.

    FFmpeg's ``m:attached_pic`` stream-specifier is not supported by every
    bundled Windows build.  Probe the disposition instead, then map the
    concrete stream index.  The tag fallback handles older files that mark
    cover art as a video stream but omit the disposition.
    """
    streams = probe(media).get("streams", [])
    attached = [
        stream for stream in streams
        if stream.get("codec_type") == "video"
        and stream.get("disposition", {}).get("attached_pic") == 1
    ]
    if not attached:
        attached = [
            stream for stream in streams
            if stream.get("codec_type") == "video"
            and "cover" in str(stream.get("tags", {}).get("comment", "")).casefold()
        ]
    # The compact ffprobe query used for the source manifest may omit
    # dispositions/tags on some Windows builds.  ``extract_embedded_cover``
    # is called only for a non-video music source, so its first video stream
    # is the conservative final fallback for attached artwork.
    if not attached:
        attached = [stream for stream in streams if stream.get("codec_type") == "video"]
    if not attached:
        return False
    stream_index = attached[0].get("index")
    if not isinstance(stream_index, int):
        return False
    result = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(media), "-map", f"0:{stream_index}", "-frames:v", "1", str(target)],
        capture_output=True,
    )
    return result.returncode == 0 and target.is_file() and target.stat().st_size > 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--music", type=Path, required=True)
    parser.add_argument("--cover", type=Path)
    parser.add_argument("--background", type=Path)
    lyrics = parser.add_mutually_exclusive_group(required=True)
    lyrics.add_argument("--lrc", type=Path)
    lyrics.add_argument("--qm", type=Path)
    parser.add_argument("--qm-roma", type=Path)
    parser.add_argument("--qmts", type=Path)
    parser.add_argument("--output", default="16x9:1920x1080")
    args = parser.parse_args()

    root = args.project_root.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit("Project root must be absent or empty; never merge source freezes")
    source, project = root / "source", root / "project"
    for directory in (source, project / "timing", project / "templates", project / "render", project / "review", project / "proposals", project / "qa", project / "work", root / "deliverables" / "review", root / "deliverables" / "final"):
        directory.mkdir(parents=True, exist_ok=True)

    frozen: list[tuple[str, Path, Path]] = []
    music_probe = probe(args.music)
    # Attached artwork in FLAC is exposed by ffprobe as a video stream. It is
    # not a music-source video and must not trigger audio extraction. Use the
    # container extension as the conservative source-role signal; explicit
    # video containers are the only inputs that should be demuxed to .mka.
    has_video = args.music.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v"}
    if has_video:
        music_target = source / "music.mka"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(args.music), "-map", "0:a:0", "-vn", "-c:a", "copy", str(music_target)], check=True)
        frozen.append(("music", args.music, music_target))
        music_origin = "derived-audio-stream-copy-from-video"
    else:
        music_target = source / f"music{args.music.suffix.lower()}"
        copy_once(args.music, music_target); frozen.append(("music", args.music, music_target)); music_origin = "direct-copy"

    if args.cover:
        original_cover = source / f"cover-original{args.cover.suffix.lower()}"
        copy_once(args.cover, original_cover); frozen.append(("coverOriginal", args.cover, original_cover))
        cover_target = source / "cover.jpg"
        Image.open(original_cover).convert("RGB").save(cover_target, quality=96, subsampling=0)
    else:
        cover_target = source / "cover.jpg"
        if not extract_embedded_cover(music_target, cover_target):
            raise SystemExit("No supplied cover and no embedded attached artwork; supply --cover")
    frozen.append(("cover", args.cover or args.music, cover_target))

    background_asset = None
    if args.background:
        background_target = source / f"background{args.background.suffix.lower()}"
        copy_once(args.background, background_target); frozen.append(("background", args.background, background_target))
        background_asset = background_target.relative_to(root).as_posix()

    if args.qm:
        lyric_pairs = [("qm", args.qm, source / "lyrics_qm.qrc")]
        if args.qm_roma: lyric_pairs.append(("qmRoma", args.qm_roma, source / "lyrics_qmRoma.qrc"))
        if args.qmts: lyric_pairs.append(("qmts", args.qmts, source / "lyrics_qmts.qrc"))
        for role, original, target in lyric_pairs: copy_once(original, target); frozen.append((role, original, target))
        lyric_manifest = {"format": "qq-music", **{role: target.relative_to(root).as_posix() for role, _, target in lyric_pairs}}
    else:
        target = source / "lyrics.lrc"; copy_once(args.lrc, target); frozen.append(("lrc", args.lrc, target))
        lyric_manifest = {"format": "lrc", "lrc": target.relative_to(root).as_posix()}

    name, dimensions = args.output.split(":", 1); width, height = (int(value) for value in dimensions.lower().split("x", 1))
    manifest = {
        "schemaVersion": 4, "slug": args.slug, "runId": "inputs-v1", "stage": "inputs_pending",
        "music": {"asset": music_target.relative_to(root).as_posix(), "origin": music_origin, "preserveCodec": True, "clock": "music"},
        "cover": {"asset": cover_target.relative_to(root).as_posix()}, "lyrics": lyric_manifest,
        "backgroundAsset": background_asset, "alignment": {"method": "none", "offsetMs": 0, "appliesTo": ["music", "lyrics", "spectrum"]},
        "outputs": [{"name": name, "width": width, "height": height, "fps": 30}],
    }
    write(project / "input-manifest.json", manifest)
    entries = []
    for role, original, target in frozen:
        entries.append({"role": role, "originalAbsolutePath": str(original.resolve()), "frozenAsset": target.relative_to(root).as_posix(), "bytes": target.stat().st_size, "sha256": sha(target), "probe": probe(target)})
    write(source / "source-manifest.json", {"schemaVersion": 1, "assets": entries})
    write(project / "build-state.json", {"schemaVersion": 2, "stage": "inputs_pending", "renderAuthorization": False, "notes": ["Sources frozen; choose preset, spectrum and alignment with configure_layers.py."]})
    print(json.dumps({"project": str(root), "music": manifest["music"], "background": background_asset, "lyrics": lyric_manifest["format"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
