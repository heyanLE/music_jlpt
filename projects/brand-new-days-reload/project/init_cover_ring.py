"""Create a cover-ring spectrum preview and project manifest."""
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).parent
PROJECT = ROOT.parent
SOURCE = PROJECT / "source"
DELIVERABLES = PROJECT / "deliverables"
AUDIO = SOURCE / "Brand New Days -Reload-.flac"
COVER = SOURCE / "COVER.jpg"
W, H, FPS, SECONDS, BANDS = 1920, 1080, 30, 10, 96
ACCENT = (215, 28, 55)

manifest = {
    "background": {"mode": "spectrum", "spectrumTemplate": "cover-ring", "spectrumBandCount": BANDS, "visibleDuringNoLyric": True},
    "foreground": {"cover": str(COVER), "lyrics": {"format": "qq-music", "qm": str(SOURCE / "lyrics_qm.qrc"), "qmRoma": str(SOURCE / "lyrics_qmRoma.qrc"), "qmts": str(SOURCE / "lyrics_qmts.qrc")}, "music": str(AUDIO), "veil": {"mode": "lyric-only", "color": "#000000", "opacity": 0.38}, "alignment": {"owner": "audio", "offsetMs": 0}},
    "canvas": {"width": W, "height": H, "fps": FPS},
}
(ROOT / "input-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "palette.json").write_text(json.dumps({"accent": "#D71C37", "activeTint": "#FF6C7F", "cardFill": "#6D0F24B8", "body": "#FFFFFF"}, indent=2), encoding="utf-8")

cover = Image.open(COVER).convert("RGB")
blur = cover.resize((W, H), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(28))
shade = Image.new("RGBA", (W, H), (10, 0, 5, 130))
background = Image.alpha_composite(blur.convert("RGBA"), shade)
side = 550
album = cover.resize((side, side), Image.Resampling.LANCZOS)
cx, cy = W // 2, H // 2 - 30

PCM = ROOT / "preview.f32le"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "0", "-t", str(SECONDS), "-i", str(AUDIO), "-ac", "1", "-ar", "8000", "-f", "f32le", str(PCM)], check=True)
import array
samples = array.array("f")
with PCM.open("rb") as fh: samples.fromfile(fh, PCM.stat().st_size // 4)
frames = ROOT / "cover_ring_preview_frames"
frames.mkdir(exist_ok=True)
window = 1024
for i in range(FPS * SECONDS):
    t = i / FPS
    at = min(len(samples) - 1, int(t * 8000))
    part = samples[max(0, at - window // 2): min(len(samples), at + window // 2)]
    energy = min(1.0, math.sqrt(sum(x*x for x in part) / max(1, len(part))) * 5.2)
    image = background.copy()
    draw = ImageDraw.Draw(image)
    # understated central disk makes the frequency ring readable at small sizes.
    draw.ellipse((cx-365, cy-365, cx+365, cy+365), fill=(0, 0, 0, 95), outline=ACCENT + (150,), width=4)
    for band in range(BANDS):
        phase = band * 0.71 + t * 5.0
        local = 0.24 + energy * (0.48 + 0.45 * ((math.sin(phase) + 1) / 2))
        inner, outer = 320, 320 + int(175 * local)
        angle = 2 * math.pi * band / BANDS - math.pi / 2
        x1, y1 = cx + math.cos(angle) * inner, cy + math.sin(angle) * inner
        x2, y2 = cx + math.cos(angle) * outer, cy + math.sin(angle) * outer
        draw.line((x1, y1, x2, y2), fill=ACCENT + (235,), width=7)
    image.alpha_composite(album.convert("RGBA"), (cx-side//2, cy-side//2))
    draw.rounded_rectangle((690, 900, 1230, 950), radius=24, fill=(0, 0, 0, 110))
    draw.text((760, 910), "Brand New Days -Reload-", fill=(255, 255, 255, 235), stroke_width=1, stroke_fill=(0,0,0,150))
    image.convert("RGB").save(frames / f"{i:04d}.jpg", quality=92)

target = DELIVERABLES / "brand-new-days-cover-ring-preview.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(frames / "%04d.jpg"), "-i", str(AUDIO), "-t", str(SECONDS), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-b:a", "320k", "-shortest", str(target)], check=True)
print(target)
