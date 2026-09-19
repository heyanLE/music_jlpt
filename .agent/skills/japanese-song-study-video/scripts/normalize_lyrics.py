#!/usr/bin/env python3
"""Decode/normalize LRC or a QQ Music QRC trio and create frame shells."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duration_ms(path: Path) -> int:
    value = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], check=True, text=True, capture_output=True).stdout.strip()
    return round(float(value) * 1000)


def decrypt_qrc(source: Path, target: Path, runtime: Path, install: bool) -> None:
    package = runtime / "node_modules" / "smart-lyric" / "package.json"
    if not package.is_file():
        if not install:
            raise SystemExit(f"QRC decoder runtime missing: {runtime}. Rerun with --install-decoder to install pinned smart-lyric@1.0.4")
        runtime.mkdir(parents=True, exist_ok=True)
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise SystemExit("npm/npm.cmd is required to install the pinned QRC decoder runtime")
        subprocess.run([npm, "install", "--prefix", str(runtime), "--no-audit", "--no-fund", "smart-lyric@1.0.4"], check=True)
    helper = Path(__file__).with_name("decode_qrc_file.mjs")
    node = shutil.which("node.exe") or shutil.which("node")
    if not node:
        raise SystemExit("node/node.exe is required to run the pinned QRC decoder runtime")
    subprocess.run([node, str(helper), str(runtime), str(source), str(target)], check=True)


def lyric_content(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    match = re.search(r'LyricContent="(.*?)"\s*/?>', raw, flags=re.S)
    return html.unescape(match.group(1)) if match else raw


def qrc_rows(path: Path) -> list[dict]:
    rows=[]
    for line in lyric_content(path).splitlines():
        match = re.match(r"^\[(\d+),(\d+)\](.*)$", line)
        if not match: continue
        start, duration, body = int(match.group(1)), int(match.group(2)), match.group(3)
        parts=[]
        for part in re.finditer(r"(.*?)\((\d+),(\d+)\)", body):
            text, part_start, part_duration = part.group(1), int(part.group(2)), int(part.group(3))
            if text: parts.append({"text": text, "startMs": part_start, "endMs": part_start + part_duration, "durationMs": part_duration})
        if parts: rows.append({"startMs": start, "endMs": start + duration, "durationMs": duration, "text": "".join(item["text"] for item in parts), "parts": parts})
    return rows


def lrc_rows(path: Path, total: int) -> list[dict]:
    rows=[]
    for line in lyric_content(path).splitlines():
        matches = list(re.finditer(r"\[(\d+):(\d+(?:\.\d+)?)\]", line))
        text = re.sub(r"\[[^\]]+\]", "", line).strip()
        if not text or text == "//" or text.startswith("TME"): continue
        for match in matches:
            start = round((int(match.group(1)) * 60 + float(match.group(2))) * 1000)
            rows.append({"startMs": start, "text": text})
    rows.sort(key=lambda item: item["startMs"])
    for index, row in enumerate(rows):
        row["endMs"] = rows[index + 1]["startMs"] if index + 1 < len(rows) else total
        row["durationMs"] = row["endMs"] - row["startMs"]
    return rows


def nearest(rows: list[dict], start: int, tolerance: int = 1600) -> dict | None:
    row = min(rows, key=lambda item: abs(item["startMs"] - start), default=None)
    return row if row and abs(row["startMs"] - start) <= tolerance else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--install-decoder", action="store_true")
    parser.add_argument("--decoder-runtime", type=Path)
    parser.add_argument("--min-lyric-ms", type=int, default=0)
    parser.add_argument("--exclude-prefix", action="append", default=[])
    args = parser.parse_args()
    root = args.project_root.resolve(); project = root / "project"; timing = project / "timing"
    manifest = load(project / "input-manifest.json"); lyrics = manifest["lyrics"]
    music_duration = duration_ms(root / manifest["music"]["asset"])
    # The decoder runtime may live in the project (per-project install) or once for the whole
    # skill (bootstrap_env.py --install-decoder); prefer the project copy, fall back to the
    # shared one so a fresh clone does not have to install it for every project.
    shared_runtime = Path(__file__).resolve().parent.parent / "runtime"
    runtime = args.decoder_runtime or project / "work" / "qrc-runtime"
    if not (runtime / "node_modules" / "smart-lyric" / "package.json").is_file() and \
            (shared_runtime / "node_modules" / "smart-lyric" / "package.json").is_file():
        runtime = shared_runtime
    excludes = tuple(args.exclude_prefix)

    if lyrics["format"] == "qq-music":
        decoded={}
        for role, output_name in (("qm", "qm-decoded.qrc"), ("qmRoma", "roma-decoded.qrc"), ("qmts", "translation-decoded.qrc")):
            if role in lyrics:
                target = timing / output_name; decrypt_qrc(root / lyrics[role], target, runtime, args.install_decoder); decoded[role] = target
        qm = qrc_rows(decoded["qm"]); roma = qrc_rows(decoded["qmRoma"]) if "qmRoma" in decoded else []
        translations = lrc_rows(decoded["qmts"], music_duration) if "qmts" in decoded else []
        displayed = [row for row in qm if row["startMs"] >= args.min_lyric_ms and not (excludes and row["text"].startswith(excludes))]
        write(timing / "qm.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": qm})
        write(timing / "roma.json", {"schemaVersion": 1, "format": "qq-qrc-word-timed", "lines": roma})
        write(timing / "translation.json", {"schemaVersion": 1, "format": "lrc-line-timed", "lines": translations})
        shells=[]
        for number, row in enumerate(displayed, 1):
            roma_row, translation_row = nearest(roma, row["startMs"]), nearest(translations, row["startMs"])
            text = row["text"]
            shells.append({
                "id": f"l{number:03}", "startMs": row["startMs"], "endMs": row["endMs"],
                "displayUnits": [{"kind": "mixed" if any(character.isascii() and character.isalpha() for character in text) else "japanese", "text": text, "qrcParts": row["parts"]}],
                "caption": {"japanese": text, "furigana": [], "romaji": roma_row["text"] if roma_row else "", "translationZh": translation_row["text"] if translation_row else "待审中文翻译"},
                "grammarCards": [], "status": "shell", "fieldProvenance": {"japanese": "timing/qm.json", "romaji": "timing/roma.json", "translationZh": "timing/translation.json"},
            })
        sources = {role: sha(root / asset) for role, asset in lyrics.items() if role != "format"}
        usable = {"japanese": "word", "romaji": "word" if roma else "absent", "translation": "line" if translations else "absent"}
    else:
        rows = lrc_rows(root / lyrics["lrc"], music_duration)
        write(timing / "lrc.json", {"schemaVersion": 1, "format": "lrc-line-timed", "lines": rows})
        shells = [{"id": f"l{index:03}", "startMs": row["startMs"], "endMs": row["endMs"], "displayUnits": [{"kind": "line", "text": row["text"]}], "caption": {"japanese": row["text"], "furigana": [], "romaji": "", "translationZh": "待审中文翻译"}, "grammarCards": [], "status": "shell", "fieldProvenance": {"japanese": "timing/lrc.json"}} for index, row in enumerate(rows, 1)]
        sources = {"lrc": sha(root / lyrics["lrc"])}; usable = {"japanese": "line", "romaji": "absent", "translation": "absent"}
    write(project / "frames.json", {"schemaVersion": 3, "frames": shells})
    write(timing / "decode-report.json", {"schemaVersion": 1, "decoder": "normalize_lyrics.py", "sources": sources, "counts": {"frameShells": len(shells)}, "usableTiming": usable, "filters": {"minLyricMs": args.min_lyric_ms, "excludePrefixes": args.exclude_prefix}})
    print(json.dumps({"frames": len(shells), "usableTiming": usable}, ensure_ascii=False))


if __name__ == "__main__":
    main()
