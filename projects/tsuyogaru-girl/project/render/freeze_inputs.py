from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
SOURCE = ROOT / "source"
PROJECT = ROOT / "project"
INPUTS = {
    "music": Path(r"C:\Users\eke_l\AppData\Local\Temp\BNZ.6a8321c87a41581\01.つよがるガール.flac"),
    "background": Path(r"C:\Users\eke_l\Desktop\【Hi-Res】败犬女主太多了_つよがるガール_feat._もっさ(ネクライトーキー)【OP】.26084835868.mp4"),
    "qmts": Path(r"C:\Users\eke_l\AppData\Roaming\Tencent\QQMusic\QQMusicCache\QQMusicLyricNew\ぼっちぼろまる_もっさ - つよがるガール (逞强好胜的女孩) - 189 - つよがるガール (逞强好胜的女孩)_qmts.qrc"),
    "qm": Path(r"C:\Users\eke_l\AppData\Roaming\Tencent\QQMusic\QQMusicCache\QQMusicLyricNew\ぼっちぼろまる_もっさ - つよがるガール (逞强好胜的女孩) - 189 - つよがるガール (逞强好胜的女孩)_qm.qrc"),
    "qmRoma": Path(r"C:\Users\eke_l\AppData\Roaming\Tencent\QQMusic\QQMusicCache\QQMusicLyricNew\ぼっちぼろまる_もっさ - つよがるガール (逞强好胜的女孩) - 189 - つよがるガール (逞强好胜的女孩)_qmRoma.qrc"),
}
NAMES = {"music": "music.flac", "background": "background.mp4", "qm": "lyrics.qm.qrc", "qmRoma": "lyrics.qmRoma.qrc", "qmts": "lyrics.qmts.qrc"}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,sample_rate,channels,bit_rate", "-of", "json", str(path)], text=True, encoding="utf-8"))
def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))

SOURCE.mkdir(parents=True, exist_ok=True)
for role, original in INPUTS.items():
    if not original.is_file(): raise FileNotFoundError(original)
    target = SOURCE / NAMES[role]
    if not target.exists(): shutil.copy2(original, target)

# FLAC contains the default cover. Extract it once into the frozen source set.
cover = SOURCE / "cover.jpg"
if not cover.exists():
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(SOURCE / "music.flac"), "-map", "0:v:0", "-frames:v", "1", str(cover)], check=True)

assets = {}
for role, name in NAMES.items():
    path = SOURCE / name
    assets[role] = {"originalPath": str(INPUTS[role]), "sourcePath": f"source/{name}", "sha256": sha(path)}
    if role in {"music", "background"}: assets[role]["probe"] = probe(path)
assets["cover"] = {"sourcePath": "source/cover.jpg", "origin": "embedded-flac-cover", "sha256": sha(cover), "probe": probe(cover)}
duration_ms = round(float(assets["music"]["probe"]["format"]["duration"]) * 1000)
video_ms = round(float(assets["background"]["probe"]["format"]["duration"]) * 1000)
dump(SOURCE / "source-manifest.json", {"schemaVersion": 1, "assets": assets})
dump(PROJECT / "assets.json", {"schemaVersion": 1, "assets": assets})
dump(PROJECT / "input-manifest.json", {
    "schemaVersion": 2, "slug": "tsuyogaru-girl", "runId": "20260817-inputs-r01",
    "title": "つよがるガール", "artist": "ぼっちぼろまる feat. もっさ（ネクライトーキー）",
    "assets": {
      "background": {"path": "source/background.mp4", "mode": "video-once-then-cover-gaussian", "sourceAudio": "mute", "videoEndMs": video_ms, "afterVideo": "cover-gaussian", "fit": "height-center-pillarbox"},
      "music": {"path": "source/music.flac", "durationMs": duration_ms}, "cover": {"path": "source/cover.jpg", "origin": "embedded-flac-cover"},
      "lyrics": {"format": "qq-music", "qm": "source/lyrics.qm.qrc", "qmRoma": "source/lyrics.qmRoma.qrc", "qmts": "source/lyrics.qmts.qrc"}
    },
    "backgroundTemplate": "video-once-then-cover-gaussian", "foregroundTemplate": {"id": "study-current-v2", "layoutApproval": "builtin"},
    "foregroundVisibility": "lyric-only", "veil": {"mode": "lyric-only", "color": "#000000", "opacity": 0.28},
    "alignment": {"clock": "audio", "offsetMs": 0}, "outputs": [{"name": "16x9", "width": 1920, "height": 1080, "fps": 30}]
})
dump(PROJECT / "build-state.json", {"schemaVersion": 2, "state": "inputs_confirmed", "runId": "20260817-inputs-r01", "completed": ["inputs_confirmed"], "next": "setup_complete", "activeFiles": {"inputManifest": "project/input-manifest.json", "sourceManifest": "source/source-manifest.json"}, "notes": ["Background plays once, then crossfades to cover Gaussian background during rendering.", "No final render is authorized."]})
