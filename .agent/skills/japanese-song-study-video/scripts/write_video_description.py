#!/usr/bin/env python3
"""Emit the episode's video description from the project's own data.

The description is part of the delivery, so it is generated - not retyped - from the
frozen build: the title line comes from the cover content (title, artist, work, role,
version), the audio line from the frozen master's real format, and the feature line from
the layers that actually exist in the presentation. Nothing claims a capability the
project does not have.

Usage
    python write_video_description.py PROJECT_ROOT [--out FILE] [--print-only]

Per-project overrides live in `project/render/description.json`; anything omitted falls
back to the series defaults below.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULTS = {
    "credits": "歌词：QQ音乐 | 文法：ds大肥鱼和我 | 校对：大家",
    "tip": "（建议直接跟唱熟悉发音，再过一遍文法解析，学唱背词更轻松~）",
    "closing": "觉得有用欢迎点赞收藏，想继续看可以关注支持一下！",
    "losslessTip": "PC 建议开启无损音质食用~",
    "baseFeatures": ["歌词 KTV 跟随", "假名", "罗马音", "中文翻译", "文法提示"],
    "extraFeatures": [],
    "version": "完整版",
}
# The series writes the container name in this casing.
CODEC_LABELS = {"flac": "Flac", "alac": "ALAC", "aac": "AAC", "mp3": "MP3", "opus": "Opus"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def audio_spec(music: Path) -> dict:
    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=codec_name,sample_rate,channels,bits_per_raw_sample", "-of", "json", str(music)],
        check=True, text=True, capture_output=True).stdout)
    stream = probe["streams"][0]
    rate = int(stream["sample_rate"])
    bits = int(stream.get("bits_per_raw_sample") or 16)
    return {"codec": stream["codec_name"], "rate": rate, "bits": bits, "channels": int(stream["channels"]),
            "text": f"{rate / 1000:g}kHz/{bits}-bit {CODEC_LABELS.get(stream['codec_name'], stream['codec_name'].upper())}"}


def build(root: Path) -> dict:
    project = root / "project"
    cover_path = project / "render" / "cover-content.json"
    if not cover_path.is_file():
        raise SystemExit(f"Cover content is missing: {cover_path.relative_to(root).as_posix()}. The description takes the "
                         "title, artist, work and role from it, so build the covers first (references/07-covers.md).")
    cover = load(cover_path)
    overrides = load(project / "render" / "description.json") if (project / "render" / "description.json").is_file() else {}
    config = {**DEFAULTS, **overrides}
    manifest = load(project / "input-manifest.json")
    master = (root / manifest["music"]["asset"]).resolve()
    spec = audio_spec(master)

    title = cover["title"]
    artist = cover["artist"]
    reading = config.get("artistReading", "")
    artist_part = f"{artist} ({reading})" if reading else artist
    work = config.get("workName")
    if not work:
        raise SystemExit("render/description.json must define workName (the work the song belongs to, e.g. 上伊那牡丹) "
                         "so the title line can name it; see references/13-video-description.md")
    role = config.get("songRole", "")
    version = config.get("version", "完整版")
    work_part = f"（《{work}》{role} {version}）" if role else f"（《{work}》{version}）"

    features = list(config["baseFeatures"])
    extras = list(config.get("extraFeatures", []))
    if extras:
        feature_line = "、".join(features) + "，以及" + "、".join(extras)
    else:
        feature_line = "、".join(features[:-1]) + "以及" + features[-1]
    audio_line = f"{spec['text']}，{config['losslessTip']}" if spec["codec"] == "flac" else \
                 f"{spec['text']}（有损编码），{config['losslessTip']}"

    text = "\n".join([
        f"《{title}》- {artist_part}{work_part}",
        f"📌 ：{config['credits']}",
        f"🎧 ：{audio_line}",
        f"📖 ： {feature_line}。",
        f" {config['tip']}",
        config["closing"],
    ]) + "\n"
    return {"text": text, "spec": spec, "fields": {"title": title, "artist": artist_part, "work": work,
                                                   "role": role, "version": version, "features": features}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--print-only", action="store_true")
    args = parser.parse_args()

    root = args.project_root.resolve()
    result = build(root)
    if args.print_only:
        sys.stdout.write(result["text"])
        return
    out = args.out or root / "deliverables" / "final" / f"{root.name}--description.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result["text"], encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(out.relative_to(root)).replace("\\", "/"), "audio": result["spec"]["text"],
                      "fields": result["fields"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
