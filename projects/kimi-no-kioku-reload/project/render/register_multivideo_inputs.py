"""Register the four extra frozen background assets and five equal scenes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
PROJECT = ROOT / "project"

EXTRA = [
    ("background-02-kotone", r"C:\Users\eke_l\Desktop\新建文件夹 (2)\Kotone animated wallpaper.mp4", "source/background-02-kotone.mp4", 3840, 2160),
    ("background-03-yukari", r"C:\Users\eke_l\Desktop\新建文件夹 (2)\Yukari animated wallpaper.mp4", "source/background-03-yukari.mp4", 1920, 1080),
    ("background-04-mitsuru", r"C:\Users\eke_l\Desktop\新建文件夹 (2)\Mitsuru animated wallpaper.mp4", "source/background-04-mitsuru.mp4", 1920, 1080),
    ("background-05-fuuka", r"C:\Users\eke_l\Desktop\新建文件夹 (2)\Fuuka animated wallpaper.mp4", "source/background-05-fuuka.mp4", 1920, 1080),
]
ORDER = [
    ("makoto", "source/background.mp4"),
    ("kotone", "source/background-02-kotone.mp4"),
    ("yukari", "source/background-03-yukari.mp4"),
    ("mitsuru", "source/background-04-mitsuru.mp4"),
    ("fuuka", "source/background-05-fuuka.mp4"),
]
TOTAL_MS = 399530
BOUNDARIES = [round(TOTAL_MS * i / 5) for i in range(6)]

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def write(path, value): path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

manifest_path = SOURCE / "source-manifest.json"
manifest = load(manifest_path)
for role, original, frozen, width, height in EXTRA:
    path = ROOT / frozen
    assert path.is_file()
    manifest["assets"] = [item for item in manifest["assets"] if item.get("role") != role]
    manifest["assets"].append({
        "role": role,
        "originalAbsolutePath": original,
        "frozenAsset": frozen,
        "bytes": path.stat().st_size,
        "sha256": sha(path),
        "probe": {
            "streams": [
                {"index": 0, "codec_name": "h264", "codec_type": "video", "width": width, "height": height, "r_frame_rate": "60/1"},
                {"index": 1, "codec_name": "aac", "codec_type": "audio"},
            ] if role != "background-05-fuuka" else [
                {"index": 0, "codec_name": "h264", "codec_type": "video", "width": width, "height": height, "r_frame_rate": "60/1"}
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "20.000000"},
        },
    })
write(manifest_path, manifest)

input_manifest = load(PROJECT / "input-manifest.json")
input_manifest["backgroundAssets"] = [asset for _, asset in ORDER]
input_manifest["audioPolicy"] = {
    "sourceCodec": "mp3", "sampleRate": 44100, "bitRate": 320000,
    "operation": "stream-copy", "lossless": False,
}
input_manifest["coverBadge"] = {
    "requested": "lossless", "eligible": False, "status": "blocked-source-is-lossy-mp3",
    "recommendedAlternative": "320 kbps",
}
write(PROJECT / "input-manifest.json", input_manifest)

fade = {"kind": "black-fade", "durationMs": 500, "scope": "background-only"}
none = {"kind": "none", "durationMs": 0, "scope": "background-only"}
segments = []
for index, (name, asset) in enumerate(ORDER):
    segments.append({
        "id": f"stage{index + 1}-{name}", "startMs": BOUNDARIES[index], "endMs": BOUNDARIES[index + 1],
        "mode": "video-loop", "asset": asset, "fit": "height-center-pillarbox", "sourceAudio": "mute",
        "foregroundMode": "follow-lyrics",
        "transitionIn": none if index == 0 else fade,
        "transitionOut": none if index == len(ORDER) - 1 else fade,
    })
write(PROJECT / "custom-scenes-input.json", {"schemaVersion": 1, "totalDurationMs": TOTAL_MS, "division": "five-equal-output-clock-segments", "segments": segments})
print(json.dumps({"registered": len(EXTRA), "boundariesMs": BOUNDARIES, "audioLossless": False}, ensure_ascii=False))
