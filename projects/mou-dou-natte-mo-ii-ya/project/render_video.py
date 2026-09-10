import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
DELIVERABLES = ROOT / "deliverables"
SLUG = "mou-dou-natte-mo-ii-ya"
FONT = "Microsoft YaHei"


def ass_escape(value):
    return value.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def ass_time(ms):
    centiseconds = round(ms / 10)
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    seconds, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{centiseconds:02}"


def extract_qrc_rows():
    raw = (DELIVERABLES / f"{SLUG}-qm-decoded.qrc").read_text(encoding="utf-8")
    content = html.unescape(re.search(r'<Lyric_1\s+[^>]*LyricContent="(.*?)"\s*/>', raw, re.DOTALL).group(1))
    rows = []
    for line in content.replace("\r\n", "\n").splitlines():
        match = re.match(r"^\[(\d+),(\d+)\](.*)$", line)
        if not match:
            continue
        start, duration, text = match.groups()
        parts = [(piece, int(part_start), int(part_duration)) for piece, part_start, part_duration in re.findall(r"(.*?)\((\d+),(\d+)\)", text) if piece]
        rows.append({"startMs": int(start), "durationMs": int(duration), "parts": parts})
    return rows


def karaoke(parts):
    chunks = []
    for text, _, duration in parts:
        chunks.append(r"{\kf%d}%s" % (max(1, round(duration / 10)), ass_escape(text)))
    return "".join(chunks)


def furigana(caption):
    return "　".join(item["text"] for item in caption["furigana"])


def make_ass(width, height):
    frames = json.loads((PROJECT / "frames.review.json").read_text(encoding="utf-8"))["frames"]
    qrc_rows = extract_qrc_rows()
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]", "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        f"Style: Furi,{FONT},32,&H00DCE3F0,&H00DCE3F0,&HAA000000,&H66000000,1,0,0,0,100,100,0,0,1,2,1,2,40,40,40,1",
        f"Style: Lyric,{FONT},60,&H00FFFFFF,&H0070B9FF,&HBB000000,&H77000000,1,0,0,0,100,100,0,0,1,3,1,2,40,40,40,1",
        f"Style: Roma,{FONT},30,&H00DCE3F0,&H0070B9FF,&HBB000000,&H77000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,40,1",
        f"Style: Zh,{FONT},34,&H00FFFFFF,&H00FFFFFF,&HBB000000,&H77000000,0,0,0,0,100,100,0,0,1,2,1,2,40,40,40,1",
        f"Style: Card,{FONT},25,&H00FFFFFF,&H00FFFFFF,&HAA000000,&HAA11151D,0,0,0,0,100,100,0,0,3,2,0,2,40,40,40,1", "",
        "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    for index, frame in enumerate(frames):
        start = frame["startMs"]
        end = start + frame["durationMs"]
        caption = frame["caption"]
        qrc = qrc_rows[index] if index < len(qrc_rows) else {"parts": []}
        top = int(height * .40)
        lyric_y = int(height * .51)
        roma_y = int(height * .60)
        zh_y = int(height * .67)
        cards_y = int(height * .79)
        begin, finish = ass_time(start), ass_time(end)
        # Black lyric-only veil, covering all elements except subtitle foreground.
        lines.append(f"Dialogue: 0,{begin},{finish},Card,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\1c&H000000&\\alpha&H80&}}m 0 0 l {width} 0 {width} {height} 0 {height}{{\\p0}}")
        reading = furigana(caption)
        if reading:
            lines.append(f"Dialogue: 2,{begin},{finish},Furi,,0,0,0,,{{\\an2\\pos({width // 2},{top})}}{ass_escape(reading)}")
        display = karaoke(qrc["parts"]) if qrc["parts"] else ass_escape(caption["japanese"])
        lines.append(f"Dialogue: 3,{begin},{finish},Lyric,,0,0,0,,{{\\an2\\pos({width // 2},{lyric_y})}}{display}")
        if caption["romaji"]:
            lines.append(f"Dialogue: 2,{begin},{finish},Roma,,0,0,0,,{{\\an2\\pos({width // 2},{roma_y})}}{ass_escape(caption['romaji'])}")
        if caption["translationZh"]:
            lines.append(f"Dialogue: 2,{begin},{finish},Zh,,0,0,0,,{{\\an2\\pos({width // 2},{zh_y})}}{ass_escape(caption['translationZh'])}")
        cards = frame["grammarCards"][:3]
        if cards:
            text = "   ".join(f"{x['token']}｜{x['reading']}｜{x.get('functionZh') or x.get('zhMeaning', '')}（{x['posZh']}）" for x in cards)
            lines.append(f"Dialogue: 1,{begin},{finish},Card,,0,0,0,,{{\\an2\\pos({width // 2},{cards_y})\\clip(40,{cards_y - 42},{width - 40},{height - 20})}}{ass_escape(text)}")
    path = PROJECT / f"overlay-{width}x{height}.ass"
    path.write_text("\n".join(lines), encoding="utf-8-sig")
    return path


def render(width, height, suffix):
    ass = make_ass(width, height)
    output = DELIVERABLES / f"{SLUG}-study-{suffix}.mp4"
    subtitle_path = ass.as_posix().replace(":", r"\:")
    scale = f"-2:{height}" if width / height >= 16 / 9 else f"{width}:-2"
    vf = f"[0:v]scale={scale},setsar=1,pad={width}:{height}:({width}-iw)/2:({height}-ih)/2:color=black,fps=30,subtitles=filename='{subtitle_path}'[v]"
    command = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(ROOT / "source" / "background.mp4"), "-i", str(ROOT / "source" / "music.flac"), "-filter_complex", vf, "-map", "[v]", "-map", "1:a:0", "-t", "91.2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True)
    return output


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    if target in ("16x9", "all"):
        print(render(1920, 1080, "16x9"))
    if target in ("4x3", "all"):
        print(render(1440, 1080, "4x3"))
