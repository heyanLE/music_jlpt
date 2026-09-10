"""Authorized clean full render for the horizontal main-lyric rail variant."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SKILL = Path("C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts")
sys.path.insert(0, str(SKILL))
from verify_render_gate import verify_render_gate

HELPER = HERE / "preview_horizontal_full_render.py"
HELPER_SHA = "95797e71b131cce1648559820ad9e20b6c1fe372f3b4fe82f1c7cdd914f6bb38"
DURATION_MS = 183844
VIDEO_END_MS = 96114


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    subprocess.run(command, check=True)


def main():
    verify_render_gate(ROOT, Path(__file__).resolve())
    if sha(HELPER) != HELPER_SHA:
        raise RuntimeError("Pinned horizontal-rail renderer dependency changed")
    presentation = json.loads((ROOT / "project/presentation.json").read_text(encoding="utf-8"))
    if presentation["foreground"]["variantId"] != "study-current-v3-static-neighbors-a":
        raise RuntimeError("Wrong foreground variant")

    run_id = "static-neighbors-r1"
    work = ROOT / "project/work" / run_id / "16x9"
    work.mkdir(parents=True, exist_ok=True)
    foreground = work / "foreground.mov"
    candidate = work / "kara-no-hako--16x9--static-neighbors-r1.mkv"
    run([sys.executable, str(HELPER), "--start-ms", "0", "--end-ms", str(DURATION_MS),
         "--foreground-mov", str(foreground), "--static-neighbors"])

    gaussian_ms = DURATION_MS - VIDEO_END_MS
    filter_graph = (
        f"[0:v]fps=30,scale=1920:1080,trim=duration={VIDEO_END_MS/1000},"
        f"fade=t=out:st={(VIDEO_END_MS-500)/1000}:d=0.5,setpts=PTS-STARTPTS[v0];"
        f"[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"gblur=sigma=45,trim=duration={gaussian_ms/1000},fade=t=in:st=0:d=0.5,setpts=PTS-STARTPTS[v1];"
        "[v0][v1]concat=n=2:v=1:a=0[bg];"
        "[bg][2:v]overlay=0:0:format=auto[mid];"
        "[mid][3:v]overlay=36:930:format=auto,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-i", str(ROOT / "source/background.mp4"), "-loop", "1", "-i",
         str(ROOT / "source/cover.jpg"), "-i", str(foreground), "-i",
         str(ROOT / "project/work/round2-approved-r1/16x9/foobar-spectrum.mov"), "-i",
         str(ROOT / "source/music.flac"), "-filter_complex", filter_graph, "-map", "[v]",
         "-map", "4:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-r", "30", "-c:a", "copy", "-t", str(DURATION_MS / 1000), str(candidate)])
    print(candidate)


if __name__ == "__main__":
    main()
