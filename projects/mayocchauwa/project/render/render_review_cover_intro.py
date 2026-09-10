"""Replace the opening three seconds with a review-safe cover slate; retain FLAC audio."""
from __future__ import annotations

import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
P, S = ROOT / "project", ROOT / "source"
RUN = P / "work" / "20260821-r03-review-cover-intro"
W, H, INTRO_SECONDS = 1920, 1080, 3
FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = max(size[0] / image.width, size[1] / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    x, y = (image.width - size[0]) // 2, (image.height - size[1]) // 2
    return image.crop((x, y, x + size[0], y + size[1]))


def make_slate(path: Path, caption: str) -> None:
    art = Image.open(S / "cover.jpg").convert("RGB")
    canvas = fit(art, (W, H)).filter(ImageFilter.GaussianBlur(28)).convert("RGBA")
    canvas.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 105)))
    cover = art.resize((700, 700), Image.Resampling.LANCZOS).convert("RGBA")
    canvas.alpha_composite(cover, ((W - cover.width) // 2, 95))
    draw = ImageDraw.Draw(canvas)
    fnt = ImageFont.truetype(FONT, 64)
    box = draw.textbbox((0, 0), caption, font=fnt, stroke_width=3)
    x = (W - (box[2] - box[0])) // 2
    y = 850
    draw.rounded_rectangle((x - 42, y - 23, x + box[2] - box[0] + 42, y + box[3] - box[1] + 23), radius=22, fill=(0, 0, 0, 150))
    draw.text((x, y), caption, font=fnt, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
    canvas.convert("RGB").save(path, quality=96)


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    scene = __import__("json").loads((P / "scene-timeline.json").read_text(encoding="utf-8"))
    intro = scene["segments"][0]
    if intro["mode"] != "cover-blur" or intro["endMs"] != 3000:
        raise RuntimeError("Expected a three-second cover-blur opening scene")
    slate = RUN / "review-cover-intro.png"; make_slate(slate, intro["caption"])
    prior = P / "work" / "20260821-r02-line-hold" / "mayocchauwa--16x9--20260821-r02-line-hold.mkv"
    candidate = RUN / "mayocchauwa--16x9--20260821-r03-review-cover-intro.mkv"
    graph = "[0:v]fps=30,format=yuv420p,setpts=PTS-STARTPTS[intro];[1:v]trim=start=3,setpts=PTS-STARTPTS,format=yuv420p[body];[intro][body]concat=n=2:v=1:a=0,fps=30[v]"
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(INTRO_SECONDS), "-i", str(slate), "-i", str(prior), "-filter_complex", graph, "-map", "[v]", "-map", "1:a:0", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr", "-c:a", "copy", str(candidate)]
    subprocess.run(cmd, check=True)
    print(candidate)


if __name__ == "__main__": main()
