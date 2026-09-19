#!/usr/bin/env python3
"""Round-trip test for the review Markdown: export, human edit, import, conflict detection.

Covers both capabilities the workspace keeps: the human-editable review document (used by
every flow) and the rule that a field both sides changed differently is reported, never
guessed.

    python test_review_markdown.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build_project(root: Path) -> None:
    project = root / "project"
    write(project / "input-manifest.json", {"schemaVersion": 4, "slug": "roundtrip"})
    write(project / "frames.json", {"schemaVersion": 3, "frames": [
        {"id": "l001", "startMs": 1000, "endMs": 2000,
         "caption": {"japanese": "茜色の夕日", "translationZh": "茜色的夕阳", "furigana": []},
         "grammarCards": [
             {"token": "茜色", "reading": "あかねいろ", "romaji": "akaneiro", "zhMeaning": "暗红色",
              "grammarStructureZh": "名词"},
             {"token": "の", "reading": "の", "romaji": "no", "functionZh": "表示所属、修饰",
              "grammarStructureZh": "格助词"},
         ]},
        {"id": "l002", "startMs": 2000, "endMs": 3000,
         "caption": {"japanese": "夕日", "translationZh": "夕阳", "furigana": []},
         "grammarCards": [{"token": "夕日", "reading": "ゆうひ", "romaji": "yuuhi", "zhMeaning": "夕阳",
                           "grammarStructureZh": "名词"}]},
    ]})
    (root / "deliverables" / "review").mkdir(parents=True, exist_ok=True)


def run(script: str, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *arguments],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def main() -> None:
    base = Path(tempfile.mkdtemp(prefix="review-md-"))
    try:
        root = base / "projects" / "roundtrip"
        build_project(root)

        exported = run("build_review_markdown.py", str(root))
        markdown = root / "deliverables" / "review" / "roundtrip-review.md"
        manifest = json.loads((root / "project" / "input-manifest.json").read_text(encoding="utf-8"))
        check("export writes the review Markdown", exported.returncode == 0 and markdown.is_file(),
              exported.stderr.strip()[:120])
        check("export records the Markdown hash in the manifest", bool(manifest.get("reviewMarkdownSha256")))
        check("export writes the baseline snapshot",
              (root / "project" / "review" / "review-markdown-baseline.json").is_file())
        text = markdown.read_text(encoding="utf-8")
        check("export uses the established section shape",
              "## l001" in text and "歌词：茜色の夕日" in text and "暂定中文：茜色的夕阳" in text
              and "- `茜色`｜あかねいろ｜akaneiro" in text)

        # A human edits a meaning and a translation.
        edited = text.replace("含义/功能：暗红色", "含义/功能：暗红色（茜草染出的红）").replace("暂定中文：夕阳", "暂定中文：落日")
        markdown.write_text(edited, encoding="utf-8", newline="\n")
        imported = run("import_review_markdown.py", str(root), "--apply")
        frames = json.loads((root / "project" / "frames.json").read_text(encoding="utf-8"))["frames"]
        check("import applies a human meaning edit",
              imported.returncode == 0 and frames[0]["grammarCards"][0]["zhMeaning"] == "暗红色（茜草染出的红）",
              imported.stderr.strip()[:120])
        check("import applies a human translation edit", frames[1]["caption"]["translationZh"] == "落日")
        report = json.loads((root / "project" / "review" / "review-markdown-import.json").read_text(encoding="utf-8"))
        check("import reports what it changed", len(report["imported"]) == 2 and report["result"] == "imported",
              json.dumps(report["imported"], ensure_ascii=False)[:140])

        # Now both sides change the same field differently: that is a conflict, never a guess.
        text = markdown.read_text(encoding="utf-8").replace("含义/功能：暗红色（茜草染出的红）", "含义/功能：暗红色（人工再改）")
        markdown.write_text(text, encoding="utf-8", newline="\n")
        frames = json.loads((root / "project" / "frames.json").read_text(encoding="utf-8"))
        frames["frames"][0]["grammarCards"][0]["zhMeaning"] = "暗红色（程序侧改动）"
        write(root / "project" / "frames.json", frames)
        conflicted = run("import_review_markdown.py", str(root), "--apply")
        after = json.loads((root / "project" / "frames.json").read_text(encoding="utf-8"))["frames"]
        report = json.loads((root / "project" / "review" / "review-markdown-import.json").read_text(encoding="utf-8"))
        check("a two-sided change is reported as a conflict", conflicted.returncode == 2 and report["conflicts"],
              json.dumps(report["conflicts"], ensure_ascii=False)[:180])
        check("a conflicting field keeps the programmatic value",
              after[0]["grammarCards"][0]["zhMeaning"] == "暗红色（程序侧改动）")

        # A token-structure change in the Markdown must not be silently applied.
        text = markdown.read_text(encoding="utf-8").replace("- `茜色`｜あかねいろ｜akaneiro", "- `茜`｜あかね｜akane")
        markdown.write_text(text, encoding="utf-8", newline="\n")
        structural = run("import_review_markdown.py", str(root), "--apply")
        report = json.loads((root / "project" / "review" / "review-markdown-import.json").read_text(encoding="utf-8"))
        check("a token-structure change is refused as a conflict",
              structural.returncode == 2
              and any(item.get("field") == "cards" for item in report["conflicts"]))
    finally:
        shutil.rmtree(base, ignore_errors=True)

    failures = [name for name, ok, _ in RESULTS if not ok]
    for name, ok, detail in RESULTS:
        print(f"[{'OK   ' if ok else 'FAIL '}] {name}" + (f"  ({detail})" if detail and not ok else ""))
    print(json.dumps({"total": len(RESULTS), "failed": len(failures)}, ensure_ascii=False))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
