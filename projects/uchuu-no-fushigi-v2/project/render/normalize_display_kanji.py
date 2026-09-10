from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\uchuu-no-fushigi-v2")
FRAMES = ROOT / "project" / "frames.json"
MERGE_ID = "display-kanji-normalization-20260817"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def normalize(caption, replacements, annotations):
    source = caption["japanese"]
    output, mapping, source_pos = [], [], 0
    for reading, display in replacements:
        hit = source.find(reading, source_pos)
        if hit < 0:
            raise ValueError(f"Cannot find {reading!r} in {source!r}")
        for index in range(source_pos, hit):
            mapping.append(len(output)); output.append(source[index])
        display_start = len(output)
        output.extend(display)
        # Multiple kana may map to the same displayed kanji; this keeps
        # QRC's per-character timing while the normalized word is visible.
        for index in range(len(reading)):
            mapping.append(display_start + min(len(display) - 1, (index * len(display)) // len(reading)))
        source_pos = hit + len(reading)
    for index in range(source_pos, len(source)):
        mapping.append(len(output)); output.append(source[index])
    caption["qrcJapanese"] = source
    caption["japanese"] = "".join(output)
    caption["sourceToDisplay"] = mapping
    caption["furigana"] = annotations


data = json.loads(FRAMES.read_text(encoding="utf-8"))
by_id = {frame["id"]: frame for frame in data["frames"]}
updates = {
    "l018": ([('ちいさな', '小さな'), ('うた', '歌')], [{"base": "小", "reading": "ちい"}, {"base": "歌", "reading": "うた"}]),
    "l019": ([('きみ', '君'), ('わすれちゃう', '忘れちゃう')], [{"base": "君", "reading": "きみ"}, {"base": "忘", "reading": "わす"}]),
    "l020": ([('ぼく', '僕'), ('おぼえている', '覚えている')], [{"base": "僕", "reading": "ぼく"}, {"base": "覚", "reading": "おぼ"}]),
    "l021": ([('おとな', '大人')], [{"base": "大人", "reading": "おとな"}]),
}
for frame_id, (replacements, annotations) in updates.items():
    frame = by_id[frame_id]
    normalize(frame["caption"], replacements, annotations)
    frame["status"] = "assisted-merged-awaiting-human-confirmation"
    provenance = frame.setdefault("fieldProvenance", {})
    provenance["caption"] = MERGE_ID
    provenance["furigana"] = MERGE_ID
write_json(FRAMES, data)
