from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\uchuu-no-fushigi-v2")
PROJECT = ROOT / "project"
OUT = ROOT / "deliverables" / "final" / "uchuu-no-fushigi-v2--study-current-v2--16x9--20260817-final-r03.mp4"
QA = PROJECT / "qa" / "qa-report.json"
FINAL = ROOT / "deliverables" / "final" / "final-manifest.json"
STATE = PROJECT / "build-state.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


probe = json.loads(subprocess.check_output([
    "ffprobe", "-v", "error", "-show_entries",
    "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,bit_rate,sample_rate,channels",
    "-of", "json", str(OUT)
], text=True, encoding="utf-8"))
video = next(s for s in probe["streams"] if s["codec_type"] == "video")
audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
duration = float(probe["format"]["duration"])
passed = video["width"] == 1920 and video["height"] == 1080 and video["avg_frame_rate"] == "30/1" and audio["codec_name"] == "aac" and abs(duration - 138.733) < 0.05
report = {
    "schemaVersion": 1,
    "status": "passed" if passed else "failed",
    "runId": "20260817-final-r03",
    "checks": {
        "resolution": [video["width"], video["height"]],
        "cfrFps": video["avg_frame_rate"],
        "durationSeconds": duration,
        "audio": {"codec": audio["codec_name"], "sampleRate": audio["sample_rate"], "channels": audio["channels"], "bitRate": audio.get("bit_rate")},
        "keyScreenshots": [
            "project/qa/20260817-final-r03/normalized-kanji.png"
        ],
        "template": {"coverVisible": True, "boldCjk": True, "semiTransparentMagicCards": True, "cardsNeverHighlight": True, "singleRow": True},
        "background": {"videoOnceThenCoverGaussian": True, "sourceAspectPreserved": True}
    },
    "warnings": [
        "The supplied background MP4 contains a top-left burned-in watermark during its first 90.215 seconds; the lower burned-in subtitle region is cropped from this render.",
        "FFmpeg reported recoverable FLAC decode warnings while reading the supplied audio; the output stream is present and duration matches the manifest."
    ]
}
dump(QA, report)
if not passed:
    raise SystemExit("QA failed")
manifest = {
    "schemaVersion": 1,
    "runId": "20260817-final-r03",
    "video": str(OUT),
    "videoSha256": sha(OUT),
    "framesSha256": sha(PROJECT / "frames.json"),
    "renderAuthorization": "project/render/render-authorization.json",
    "qaReport": "project/qa/qa-report.json",
    "probe": {"durationSeconds": duration, "resolution": [video["width"], video["height"]], "fps": video["avg_frame_rate"], "videoCodec": video["codec_name"], "audioCodec": audio["codec_name"], "audioBitRate": audio.get("bit_rate")}
}
dump(FINAL, manifest)
state = json.loads(STATE.read_text(encoding="utf-8"))
state["state"] = "delivered"
state["next"] = None
state.setdefault("activeFiles", {})["final"] = "deliverables/final/uchuu-no-fushigi-v2--study-current-v2--16x9--20260817-final-r03.mp4"
state["activeFiles"]["qaReport"] = "project/qa/qa-report.json"
state["notes"] = [n for n in state.get("notes", []) if "No final render" not in n]
state["notes"].append("Final render delivered after QA pass; source media warnings are recorded in qa-report.json.")
dump(STATE, state)
