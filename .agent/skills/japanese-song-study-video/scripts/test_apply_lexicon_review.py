#!/usr/bin/env python3
"""Test apply_lexicon_review.py on a throwaway project (synthetic queue + review)."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SCRIPTS = Path(r"C:\project\musicjlpt\.agent\skills\japanese-song-study-video\scripts")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build(root: Path) -> None:
    project = root / "project"
    write(project / "frames.json", {"schemaVersion": 3, "frames": [
        {"id": "l001", "startMs": 1000, "endMs": 2000,
         "caption": {"japanese": "遠くなって 灯りは無常", "furigana": [], "translationZh": "皆已渐行渐远 灯火如无常浮世"},
         "grammarCards": [{"token": "遠く", "reading": "とおく", "romaji": "tooku", "zhMeaning": "远",
                           "grammarStructureZh": "形容词", "status": "rag-proposed-low-confidence", "reviewRequired": True}]},
        {"id": "l002", "startMs": 3000, "endMs": 4000,
         "caption": {"japanese": "心揺らいでる", "furigana": [], "translationZh": "心中暗潮汹涌"},
         "grammarCards": []},
    ]})
    write(project / "review" / "rag-review-queue.json", {
        "schemaVersion": 1, "lexiconSha256": "a" * 64,
        "totals": {"frames": 2, "cardsDrafted": 1, "lowConfidenceProposed": 1, "reviewUnits": 2},
        "queue": [
            {"frameId": "l001", "japanese": "遠くなって 灯りは無常", "units": [{"text": "灯りは無常"}]},
            {"frameId": "l002", "japanese": "心揺らいでる", "units": [{"text": "心揺らいでる"}]},
        ],
    })
    write(project / "review" / "online-review.json", {
        "schemaVersion": 1, "reviewRole": "online", "status": "completed", "lexiconSha256": "a" * 64,
        "changes": [
            {"frameId": "l001", "unit": "灯りは無常",
             "resolution": "灯り(あかり) + は + 無常(むじょう)",
             "cards": [
                 {"token": "遠く", "reading": "とおく", "romaji": "tooku", "zhMeaning": "远", "grammarStructureZh": "形容词"},
                 {"token": "なって", "reading": "なって", "romaji": "natte", "zhMeaning": "变得", "grammarStructureZh": "动词て形"},
                 {"token": "灯り", "reading": "あかり", "romaji": "akari", "zhMeaning": "灯火", "grammarStructureZh": "名词"},
                 {"token": "は", "reading": "は", "romaji": "wa", "functionZh": "提示主题", "grammarStructureZh": "提示助词"},
                 {"token": "無常", "reading": "むじょう", "romaji": "mujou", "zhMeaning": "无常", "grammarStructureZh": "名词"},
             ],
             "furigana": [{"base": "遠", "reading": "とお"}, {"base": "灯", "reading": "あか"}, {"base": "無常", "reading": "むじょう"}],
             "confidence": "high", "evidence": ["https://example.test — 無常=むじょう"]},
            {"frameId": "l002", "unit": "心揺らいでる",
             "resolution": "心 + 揺らいでる",
             "cards": [
                 {"token": "心", "reading": "こころ", "romaji": "kokoro", "zhMeaning": "心", "grammarStructureZh": "名词"},
                 {"token": "揺らいでる", "reading": "ゆらいでる", "romaji": "yuraideru", "zhMeaning": "动摇着", "grammarStructureZh": "动词て形＋いる"},
             ],
             "confidence": "high", "evidence": ["lexicon entry 心"]},
        ],
    })


def run(root: Path, dry: bool = False) -> subprocess.CompletedProcess:
    command = [sys.executable, str(SCRIPTS / "apply_lexicon_review.py"), str(root)]
    if dry:
        command.append("--dry-run")
    return subprocess.run(command, capture_output=True, text=True)


def main() -> None:
    base = Path(tempfile.mkdtemp(prefix="apply-review-"))
    checks = []
    try:
        root = base / "projects" / "sandbox"
        build(root)
        dry = run(root, dry=True)
        frames_after_dry = sha(root / "project" / "frames.json")
        checks.append(("dry run succeeds without writing", dry.returncode == 0 and frames_after_dry == sha(root / "project" / "frames.json")))

        applied = run(root)
        document = json.loads((root / "project" / "frames.json").read_text(encoding="utf-8"))
        by_id = {frame["id"]: frame for frame in document["frames"]}
        checks.append(("apply succeeds", applied.returncode == 0))
        checks.append(("reviewed cards replace the draft", [card["token"] for card in by_id["l001"]["grammarCards"]]
                       == ["遠く", "なって", "灯り", "は", "無常"]))
        checks.append(("cards are marked online-reviewed",
                       all(card["status"] == "online-reviewed" and card["reviewRequired"] is False for card in by_id["l002"]["grammarCards"])))
        checks.append(("ruby anchors match the lyric",
                       all(by_id["l001"]["caption"]["japanese"][item["start"]:item["end"]] == item["base"]
                           for item in by_id["l001"]["caption"]["furigana"])))
        merge_log = json.loads((root / "project" / "review" / "rag-review-merge-log.json").read_text(encoding="utf-8"))
        checks.append(("merge log binds both frame hashes",
                       merge_log["framesAfterSha256"] == sha(root / "project" / "frames.json")
                       and merge_log["framesBeforeSha256"] != merge_log["framesAfterSha256"]))

        # A unit left unanswered must be refused.
        review_path = root / "project" / "review" / "online-review.json"
        review = json.loads(review_path.read_text(encoding="utf-8"))
        review["changes"] = review["changes"][:1]
        write(review_path, review)
        incomplete = run(root)
        checks.append(("incomplete review is refused", incomplete.returncode != 0 and "does not match the queue" in incomplete.stderr))

        # A card with both meaning fields must be refused (with the queue covered again,
        # so the card rule - not the coverage rule - is what rejects it).
        build(root)
        review = json.loads((root / "project" / "review" / "online-review.json").read_text(encoding="utf-8"))
        review["changes"][0]["cards"][0]["functionZh"] = "也表示功能"
        write(root / "project" / "review" / "online-review.json", review)
        both_fields = run(root)
        checks.append(("card with two meaning fields is refused",
                       both_fields.returncode != 0 and "exactly one" in both_fields.stderr))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    failures = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[{'OK   ' if ok else 'FAIL '}] {name}")
    print(json.dumps({"total": len(checks), "failed": len(failures)}, ensure_ascii=False))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
