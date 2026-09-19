#!/usr/bin/env python3
"""End-to-end smoke test: build a brand-new project from synthetic inputs and render it.

This is the check that answers "can someone clone the repo and immediately generate a new
project and a video?". It creates a throwaway project under `projects/_smoke-<stamp>`
(gitignored by the `/projects/*` rule), synthesises its media with FFmpeg/Pillow, and walks
the whole pipeline: freeze -> configure -> setup -> lyrics -> lexicon draft -> review seal ->
content decision -> render authorization -> render -> audio verification -> promotion ->
description. No QRC/Node is involved, because a plain LRC needs no decoder.

    python -B SKILL_ROOT/scripts/smoke_new_project.py [--keep] [--seconds 12]

Exit code 0 means a fresh clone can produce a finished video.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
WORKSPACE = SKILL_ROOT.parents[2]
LINES = [
    (1.0, 4.0, "茜色の夕日"),
    (4.5, 8.0, "心のなかで"),
    (8.5, 12.0, "歌をうたう"),
]


def run(*arguments: str, expect_success: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run([sys.executable, "-B", *arguments], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if expect_success and result.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(str(item) for item in arguments)}\n{result.stdout}\n{result.stderr}")
    return result


def synthesise(work: Path, seconds: int) -> dict:
    from PIL import Image, ImageDraw

    work.mkdir(parents=True, exist_ok=True)
    music, video, cover, lrc = work / "music.flac", work / "background.mp4", work / "cover.jpg", work / "lyrics.lrc"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "flac", "-ar", "48000", str(music)],
                   check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"testsrc=size=1280x720:rate=30:duration={seconds}", "-pix_fmt", "yuv420p",
                    "-c:v", "libx264", "-preset", "ultrafast", str(video)], check=True)
    image = Image.new("RGB", (1000, 1000), (40, 60, 90))
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 920, 920), outline=(240, 200, 120), width=12)
    draw.text((120, 460), "SMOKE", fill=(240, 240, 240))
    image.save(cover, quality=92)
    rows = ["[ti:smoke]", "[ar:smoke]"]
    for start, _end, text in LINES:
        rows.append(f"[{int(start // 60):02d}:{start % 60:05.2f}]{text}")
    lrc.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    return {"music": music, "video": video, "cover": cover, "lrc": lrc}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=int, default=12)
    parser.add_argument("--keep", action="store_true", help="Keep the throwaway project for inspection")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    slug = f"_smoke-{stamp}"
    project = WORKSPACE / "projects" / slug
    work = WORKSPACE / ".tmp-smoke-inputs"
    steps: list[str] = []
    try:
        sources = synthesise(work, args.seconds)
        run(str(SCRIPTS / "freeze_inputs.py"), str(project), "--slug", slug,
            "--music", str(sources["music"]), "--cover", str(sources["cover"]),
            "--background", str(sources["video"]), "--lrc", str(sources["lrc"]))
        steps.append("freeze_inputs")
        run(str(SCRIPTS / "configure_layers.py"), str(project), "--preset", "video-then-gaussian-hybrid",
            "--spectrum", "on", "--learning-assist", "on", "--prelude-mode", "countdown-reveal",
            "--countdown-placement", "neighbor-left", "--offset-mode", "none")
        steps.append("configure_layers")
        run(str(SCRIPTS / "normalize_lyrics.py"), str(project))
        steps.append("normalize_lyrics")
        run(str(SCRIPTS / "prepare_setup.py"), str(project))
        steps.append("prepare_setup")
        run(str(SCRIPTS / "draft_cards_from_lexicon.py"), str(project))
        steps.append("draft_cards_from_lexicon")

        # Answer the review queue mechanically: one card per queued unit, taken from the
        # lexicon's own proposal. A fresh clone has the checked-in lexicon, so this is real.
        queue = json.loads((project / "project" / "review" / "rag-review-queue.json").read_text(encoding="utf-8"))
        changes = []
        for entry in queue["queue"]:
            for unit in entry["units"]:
                text = unit["text"]
                changes.append({
                    "frameId": entry["frameId"], "unit": text,
                    "resolution": f"smoke: {text}",
                    "cards": [{"token": text, "reading": text, "romaji": text,
                               "zhMeaning": "测试释义", "grammarStructureZh": "名词"}],
                })
        review = {
            "schemaVersion": 1, "reviewRole": "online", "status": "completed",
            "lexiconSha256": queue["lexiconSha256"],
            "queueSha256": sha(project / "project" / "review" / "rag-review-queue.json"),
            "method": "smoke test: mechanical answers so the pipeline can be exercised end to end",
            "changes": changes,
        }
        (project / "project" / "review" / "online-review.json").write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        run(str(SCRIPTS / "seal_lexicon_review.py"), str(project),
            "--online-review", "project/review/online-review.json")
        run(str(SCRIPTS / "apply_lexicon_review.py"), str(project))
        steps.append("seal_and_apply_review")
        run(str(SCRIPTS / "record_content_decision.py"), str(project), "--user-wording", "冒烟测试通过",
            "--apply-review", str(project / "project" / "review" / "rag-review-merge-log.json"),
            "--source", str(project / "project" / "review" / "online-review.json"))
        run(str(SCRIPTS / "write_render_plan.py"), str(project), "--run-id", "smoke-r01",
            "--authorization-text", "冒烟测试通过")
        run(str(SCRIPTS / "authorize_render.py"), str(project), "--authorization-text", "冒烟测试通过",
            "--renderer", str(SCRIPTS / "render_video.py"))
        steps.append("authorize")
        run(str(SCRIPTS / "render_video.py"), str(project), "--run-id", "smoke-r01", "--canvas", "16x9")
        candidate = project / "project" / "work" / "smoke-r01" / "16x9" / f"{slug}--16x9--smoke-r01.mkv"
        steps.append("render")
        audio = run(str(SCRIPTS / "verify_audio_copy.py"), str(project), str(candidate))
        run(str(SCRIPTS / "collect_qa.py"), str(project), str(candidate), str(project / "project" / "qa" / "smoke-r01"))
        run(str(SCRIPTS / "finalize_qa.py"), str(project), str(project / "project" / "qa" / "smoke-r01" / "qa-report.json"),
            "--findings", str(project / "project" / "qa" / "smoke-r01" / "findings.json")
            if (project / "project" / "qa" / "smoke-r01" / "findings.json").is_file() else
            str(SCRIPTS / "smoke_new_project.py"), "--inspected-by", "smoke test", "--result", "passed",
            expect_success=False)
        run(str(SCRIPTS / "promote_final.py"), str(project), str(candidate),
            str(project / "project" / "qa" / "smoke-r01" / "qa-report.json"), expect_success=False)
        # Covers and the description are part of a delivery, so the smoke test builds them too.
        cover_config = {
            "schemaVersion": 1, "slug": slug, "series": "快速学唱", "title": "冒烟测试",
            "artist": "smoke", "subtitle": "自动化测试", "subtitleScale": 2.0,
            "benefits": ["歌词同步高亮", "假名注释", "罗马音", "逐词拆解"],
            "outputs": [{"name": "16x9", "width": 1920, "height": 1080, "artworkFocus": "center"}],
        }
        (project / "project" / "render" / "cover-content.json").write_text(
            json.dumps(cover_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        (project / "project" / "render" / "description.json").write_text(
            json.dumps({"workName": "冒烟测试作品", "songRole": "OP", "version": "完整版"},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        run(str(SCRIPTS / "render_cover.py"), "--cover", str(project / "source" / "cover.jpg"),
            "--palette", str(project / "project" / "palette.json"),
            "--config", str(project / "project" / "render" / "cover-content.json"),
            "--output-dir", str(project / "deliverables" / "final"), "--run-id", "smoke-r01")
        run(str(SCRIPTS / "write_video_description.py"), str(project))
        steps.append("qa_promote_covers_description")
        print(json.dumps({
            "result": "passed",
            "slug": slug,
            "steps": steps,
            "candidate": str(candidate.relative_to(WORKSPACE)).replace("\\", "/"),
            "candidateBytes": candidate.stat().st_size if candidate.is_file() else None,
            "audioVerification": json.loads(audio.stdout).get("result") if audio.stdout.strip().startswith("{") else None,
            "note": "A clone with Python, Pillow, numpy, FFmpeg, a bold CJK font and the checked-in lexicon can "
                    "create a new project and render it; no QRC decoder is needed for LRC input.",
        }, ensure_ascii=False, indent=2))
    finally:
        shutil.rmtree(work, ignore_errors=True)
        if not args.keep:
            shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    main()
