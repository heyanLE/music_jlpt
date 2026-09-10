#!/usr/bin/env python3
"""Render a reviewed fixed-preset project as background -> foreground -> overlay.

The candidate stays under project/work. Promotion still requires visual QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
SKILL_SCRIPTS = Path('C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts')
sys.path.append(str(SKILL_SCRIPTS))
assert hashlib.sha256(Path(__file__).with_name('foreground_layout.py').read_bytes()).hexdigest() == '06ae7ece5546fb9ae10a175c1b9d40b1e43e43ec074c3ffc738134c139b4480e', 'Layout helper changed: rebind renderer and obtain fresh authorization'
from foreground_layout import plan, qrc_spans
from verify_render_gate import sha, verify_render_gate


FONT = Path("C:/Windows/Fonts/msyhbd.ttc")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def probe(path: Path) -> dict:
    return json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,sample_rate,bits_per_raw_sample", "-of", "json", str(path)],
        check=True, text=True, capture_output=True,
    ).stdout)


def norm(text: str) -> str:
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int, balance: bool = False) -> list[str]:
    lines, current = [], ""
    for character in text:
        proposal = current + character
        if current and draw.textbbox((0, 0), proposal, font=font)[2] > width:
            lines.append(current); current = character
        else:
            current = proposal
    if current: lines.append(current)
    if balance and len(lines) == 2:
        candidates = []
        for split in range(1, len(text)):
            left, right = text[:split], text[split:]
            if left[-1] in '（([' or right[0] in '）)]，。、；：！？':
                continue
            a = draw.textbbox((0, 0), left, font=font)[2]
            b = draw.textbbox((0, 0), right, font=font)[2]
            if max(a, b) <= width:
                candidates.append((abs(a-b), left, right))
        if candidates:
            _, left, right = min(candidates)
            lines = [left, right]
    return lines


def apply_cover_visibility_overrides(segments: list[dict], overrides: list[dict] | None) -> list[dict]:
    """Split foreground states at output-clock boundaries and set cover visibility.

    The split is necessary because a lyric/highlight state can span an override
    boundary.  Only the cover flag changes; every other foreground field is
    copied verbatim.
    """
    if not overrides:
        return [{**segment, "coverVisible": True} for segment in segments]

    ranges: list[tuple[int, int, bool]] = []
    for item in overrides:
        if item.get("clock", "output") != "output":
            raise RuntimeError("coverVisibilityOverrides currently supports output clock only")
        start, end = int(item["startMs"]), int(item["endMs"])
        visible = item.get("visible")
        if start < 0 or end <= start or not isinstance(visible, bool):
            raise RuntimeError(f"Invalid cover visibility override: {item}")
        ranges.append((start, end, visible))
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if current[0] < previous[1]:
            raise RuntimeError("coverVisibilityOverrides must not overlap")

    result: list[dict] = []
    boundaries = {value for start, end, _visible in ranges for value in (start, end)}
    for segment in segments:
        segment_start, segment_end = int(segment["startMs"]), int(segment["endMs"])
        points = [segment_start, *sorted(value for value in boundaries if segment_start < value < segment_end), segment_end]
        for start, end in zip(points, points[1:]):
            visible = True
            for range_start, range_end, range_visible in ranges:
                if range_start <= start and end <= range_end:
                    visible = range_visible
                    break
            result.append({**segment, "startMs": start, "endMs": end, "coverVisible": visible})
    return result


class ForegroundRenderer:
    def __init__(self, root: Path, width: int, height: int):
        self.root, self.project, self.source = root, root / "project", root / "source"
        self.width, self.height = width, height
        self.sx, self.sy, self.scale = width / 1920, height / 1080, min(width / 1920, height / 1080)
        self.palette = load(self.project / "palette.json")
        self.presentation = load(self.project / "presentation.json")["foreground"]
        self.frames = {item["id"]: item for item in load(self.project / "frames.json")["frames"]}
        timing_path = self.project / "timing" / "qm.json"
        if not timing_path.is_file(): timing_path = self.project / "timing" / "lrc.json"
        self.rows = load(timing_path)["lines"]
        self.cover = Image.open(root / load(self.project / "input-manifest.json")["cover"]["asset"]).convert("RGBA")

    def px(self, value: float, axis: str = "uniform") -> int:
        return round(value * ({"x": self.sx, "y": self.sy, "uniform": self.scale}[axis]))

    def font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(FONT, max(8, self.px(size)))

    def fit(self, draw: ImageDraw.ImageDraw, text: str, start: int, minimum: int, width: int) -> ImageFont.FreeTypeFont:
        for size in range(self.px(start), self.px(minimum) - 1, -1):
            candidate = ImageFont.truetype(FONT, max(8, size))
            if draw.textbbox((0, 0), text, font=candidate)[2] <= width:
                return candidate
        raise RuntimeError(f"Text cannot fit without becoming unreadable: {text}")

    def outlined(self, draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, font: ImageFont.FreeTypeFont, fill, stroke: int) -> None:
        width = self.px(stroke) if self.presentation.get("textOutline", {}).get("enabled", True) else 0
        draw.text(xy, text, font=font, fill=fill, stroke_width=width, stroke_fill=self.presentation.get("textOutline", {}).get("color", "#000000"))

    def matched_parts(self, frame: dict) -> list[dict]:
        target = norm(frame["caption"]["japanese"])
        indices = [index for index, row in enumerate(self.rows) if row["startMs"] == frame["startMs"]]
        for index in indices:
            if norm(self.rows[index]["text"]) == target and not self.rows[index].get("parts"):
                return [{"text": self.rows[index]["text"]}]
            text, parts = "", []
            for row in self.rows[index:index + 4]:
                text += row["text"]; parts.extend(row.get("parts", []))
                if norm(text) == target: return parts
                if len(norm(text)) > len(target): break
        return [{"text": frame["caption"]["japanese"]}]

    def render(self, frame_id: str | None, active_index: int | None, output: Path, cover_only: bool = False, cover_visible: bool = True) -> None:
        image = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        if cover_only:
            if cover_visible:
                cover_rect = (self.px(850, "x"), self.px(35, "y"), self.px(220, "x"), self.px(220, "y"))
                image.alpha_composite(self.cover.resize((cover_rect[2], cover_rect[3]), Image.Resampling.LANCZOS), (cover_rect[0], cover_rect[1]))
            output.parent.mkdir(parents=True, exist_ok=True); image.save(output); return
        if frame_id is None:
            image.save(output); return
        frame = self.frames[frame_id]
        opacity = round(float(self.presentation.get("veil", {}).get("opacity", .28)) * 255)
        veil = rgb(self.presentation.get("veil", {}).get("color", "#000000")) + (opacity,)
        image.alpha_composite(Image.new("RGBA", image.size, veil))
        if cover_visible:
            cover_rect = (self.px(850, "x"), self.px(35, "y"), self.px(220, "x"), self.px(220, "y"))
            image.alpha_composite(self.cover.resize((cover_rect[2], cover_rect[3]), Image.Resampling.LANCZOS), (cover_rect[0], cover_rect[1]))
        draw = ImageDraw.Draw(image); text = frame["caption"]["japanese"]
        lyric_font = self.fit(draw, text, 70, 53, self.px(1728, "x"))
        layout = plan(frame, draw, lyric_font, self.font(28), self.font(34), self.font(23), self.px(14))
        if layout['width'] > self.px(1728, 'x'):
            raise RuntimeError(f"Annotated lyric exceeds width: {frame_id} {layout['width']}")
        self.last_layout = layout
        lyric_x = (self.width - layout['width']) / 2
        body, active = (255, 255, 255, 242), rgb(self.palette["activeTint"]) + (255,)
        parts = self.matched_parts(frame)
        part_ranges = qrc_spans(text, parts)
        active_span = part_ranges[active_index] if active_index is not None and 0 <= active_index < len(part_ranges) else None

        card_spans, search_cursor = [], 0
        for card in frame.get("grammarCards", []):
            token = card["token"]
            start = text.find(token, search_cursor)
            if start < 0:
                card_spans.append(None)
                continue
            end = start + len(token)
            card_spans.append((start, end))
            search_cursor = end

        def is_active(start: int, end: int) -> bool:
            return bool(active_span and start < active_span[1] and active_span[0] < end)

        active_cards = [span for span in card_spans if span and is_active(*span)]
        for index, value in enumerate(text):
            highlighted = is_active(index, index+1) or any(a <= index < b for a,b in active_cards)
            self.outlined(draw, (lyric_x+layout['xs'][index], self.px(330, "y")), value, lyric_font, active if highlighted else body, 4)

        # Ruby is authoritative render content, not a value reconstructed from
        # grammar-card readings. Card tokens may include literal kana, so using
        # their full reading here duplicates kana and can also reintroduce stale
        # readings after a caption correction.
        ruby_font = self.font(28)
        for ruby in frame["caption"].get("furigana", []):
            if "start" in ruby and "end" in ruby:
                start, end = int(ruby["start"]), int(ruby["end"])
            else:
                card_index = int(ruby["cardIndex"])
                if card_index < 0 or card_index >= len(card_spans) or card_spans[card_index] is None:
                    raise RuntimeError(f"Furigana card anchor mismatch in {frame_id}: {ruby}")
                start = card_spans[card_index][0] + int(ruby.get("surfaceOffset", 0))
                end = start + len(ruby["base"])
            if text[start:end] != ruby["base"]:
                raise RuntimeError(f"Furigana anchor mismatch in {frame_id}: {ruby}")
            ruby_x = lyric_x + layout['xs'][start]
            highlighted = is_active(start,end) or any(start < b and a < end for a,b in active_cards)
            self.outlined(draw, (ruby_x, self.px(295, "y")), ruby["reading"], ruby_font, active if highlighted else body, 2)

        for card_index, card in enumerate(frame.get("grammarCards", [])):
            token = card["token"]
            if card_index >= len(card_spans) or card_spans[card_index] is None:
                continue
            start, end = card_spans[card_index]
            block = next(b for b in layout['blocks'] if b['cardIndex'] == card_index)
            token_fill = active if is_active(start, end) else body
            if card.get("sourceWord"):
                annotation_font = self.font(23); annotation_width = draw.textbbox((0, 0), card["sourceWord"], font=annotation_font)[2]
                self.outlined(draw, (lyric_x+block['sourceX'], self.px(295, "y")), card["sourceWord"], annotation_font, token_fill, 2)
            romaji = card.get("romaji", "")
            if romaji:
                romaji_font = self.font(34); romaji_width = draw.textbbox((0, 0), romaji, font=romaji_font)[2]
                self.outlined(draw, (lyric_x+block['romajiX'], self.px(430, "y")), romaji, romaji_font, token_fill, 2)

        if self.presentation.get("lineTranslation", {}).get("enabled", True):
            translation = frame["caption"].get("translationZh", "")
            translation_font = self.font(45); translation_lines = wrap(draw, translation, translation_font, self.px(1651, "x"))
            if len(translation_lines) > 2: raise RuntimeError(f"Line translation exceeds two lines: {frame_id}")
            for index, line in enumerate(translation_lines):
                line_width = draw.textbbox((0, 0), line, font=translation_font)[2]
                self.outlined(draw, ((self.width - line_width) / 2, self.px(500 + index * 52, "y")), line, translation_font, (245, 245, 245, 245), 3)

        cards = frame.get("grammarCards", [])
        if cards:
            gap, total, x = self.px(12), self.px(1730, "x"), self.px(95, "x")
            card_width = (total - gap * (len(cards) - 1)) // len(cards)
            for card in cards:
                right = x + card_width; layer = Image.new("RGBA", image.size, (0, 0, 0, 0)); layer_draw = ImageDraw.Draw(layer)
                alpha = round(float(self.palette.get("cardFill", {}).get("alpha", .75)) * 255)
                layer_draw.rounded_rectangle((x, self.px(600, "y"), right, self.px(850, "y")), radius=self.px(20), fill=rgb(self.palette["accent"]) + (alpha,), outline=rgb(self.palette["activeTint"]) + (220,), width=max(1, self.px(2)))
                image.alpha_composite(layer); draw = ImageDraw.Draw(image); inner = card_width - self.px(28)
                token_font = self.fit(draw, card["token"], 37, 16, inner)
                # Keep the card's third row concise: long grammar explanations
                # remain in frames.json and the review document only.
                # grammarStructureZh is the reviewed canonical field. posZh is
                # retained only for importing older projects.
                grammar = card.get("grammarStructureZh") or card.get("posZh", "")
                grammar_font = self.fit(draw, grammar, 25, 14, inner)
                meaning = card.get("functionZh", card.get("zhMeaning", "")); meaning_font = self.font(26)
                meaning_lines = wrap(draw, meaning, meaning_font, inner, balance=True)
                if len(meaning_lines) > 2: raise RuntimeError(f"Card meaning exceeds two fixed-size lines: {frame_id} {card['token']}")
                for y, value, field_font in ((625, card["token"], token_font), (770, grammar, grammar_font)):
                    field_width = draw.textbbox((0, 0), value, font=field_font)[2]
                    self.outlined(draw, (x + (card_width - field_width) / 2, self.px(y, "y")), value, field_font, "white", 2)
                top = 695 if len(meaning_lines) == 1 else 678
                for index, line in enumerate(meaning_lines):
                    line_width = draw.textbbox((0, 0), line, font=meaning_font)[2]
                    self.outlined(draw, (x + (card_width - line_width) / 2, self.px(top + index * 32, "y")), line, meaning_font, "white", 2)
                x = right + gap
        output.parent.mkdir(parents=True, exist_ok=True); image.save(output)


def background_inputs_and_filter(root: Path, scenes: list[dict], width: int, height: int, duration_ms: int) -> tuple[list[str], str, int]:
    args, labels, elapsed = [], [], 0
    for index, scene in enumerate(scenes):
        asset = root / scene["asset"]
        if scene["mode"] == "video-loop": args += ["-stream_loop", "-1", "-i", str(asset)]
        elif scene["mode"] == "cover-gaussian": args += ["-loop", "1", "-i", str(asset)]
        else: args += ["-i", str(asset)]
        end = duration_ms if scene["endMs"] == "audio-end" else int(scene["endMs"])
        segment_duration = (end - int(scene["startMs"])) / 1000
        if segment_duration <= 0: raise RuntimeError(f"Invalid scene duration: {scene['id']}")
        if scene["mode"] in ("video-loop", "video-clip"):
            chain = f"[{index}:v]fps=30,scale=-2:{height},crop='min(iw,{width})':{height},pad={width}:{height}:(ow-iw)/2:(oh-ih):black,trim=duration={segment_duration:.6f},setpts=PTS-STARTPTS"
        elif scene["mode"] == "cover-gaussian":
            chain = f"[{index}:v]fps=30,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},gblur=sigma=30,eq=brightness=-0.25,trim=duration={segment_duration:.6f},setpts=PTS-STARTPTS"
        else:
            raise RuntimeError(f"Fixed renderer does not support custom background mode {scene['mode']}")
        fade_in, fade_out = scene.get("transitionIn", {}), scene.get("transitionOut", {})
        if fade_in.get("kind") in ("black-fade", "white-fade") and fade_in.get("durationMs", 0):
            color = "white" if fade_in["kind"] == "white-fade" else "black"
            chain += f",fade=t=in:st=0:d={fade_in['durationMs']/2000:.6f}:color={color}"
        if fade_out.get("kind") in ("black-fade", "white-fade") and fade_out.get("durationMs", 0):
            color = "white" if fade_out["kind"] == "white-fade" else "black"
            half = fade_out["durationMs"] / 2000
            chain += f",fade=t=out:st={max(0, segment_duration-half):.6f}:d={half:.6f}:color={color}"
        label = f"bg{index}"; labels.append(f"[{label}]"); args_label = f"{chain}[{label}]"
        labels[-1] = args_label
        elapsed += end - int(scene["startMs"])
    filter_parts = labels
    input_labels = "".join(f"[bg{i}]" for i in range(len(scenes)))
    filter_parts.append(f"{input_labels}concat=n={len(scenes)}:v=1:a=0[background]")
    return args, ";".join(filter_parts), len(scenes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--canvas", help="Required when input-manifest declares multiple outputs")
    parser.add_argument("--output-name")
    args = parser.parse_args()
    root = args.project_root.resolve(); project = root / "project"
    verify_render_gate(root, Path(__file__).resolve())
    manifest = load(project / "input-manifest.json"); presentation = load(project / "presentation.json")
    scenes = load(project / "scene-timeline.json")["segments"]
    if manifest.get("pipelinePreset") not in ("video-loop-follow", "video-then-gaussian-hybrid", "gaussian-persistent"):
        raise SystemExit("render_video.py handles fixed presets only; custom requires a documented project renderer")
    outputs = manifest.get("outputs", [{"name": "16x9", "width": 1920, "height": 1080, "fps": 30}])
    if len(outputs) > 1 and not args.canvas:
        raise SystemExit("Multiple outputs declared; rerun once per output with --canvas NAME")
    canvas = next((item for item in outputs if item.get("name") == args.canvas), outputs[0] if not args.canvas else None)
    if canvas is None: raise SystemExit(f"Unknown canvas: {args.canvas}")
    width, height, fps = int(canvas["width"]), int(canvas["height"]), int(canvas.get("fps", 30))
    if fps != 30: raise SystemExit("Fixed renderer supports CFR 30 only")
    music = root / manifest["music"]["asset"]; music_probe = probe(music)
    music_duration = round(float(music_probe["format"]["duration"]) * 1000)
    offset = int(manifest.get("alignment", {}).get("offsetMs", 0)); duration_ms = max(1, music_duration + offset)
    run = project / "work" / args.run_id / canvas.get("name", "canvas"); foreground_dir = run / "foreground"; foreground_dir.mkdir(parents=True, exist_ok=True)
    timeline_path = run / "foreground-timeline.json"
    subprocess.run([sys.executable, str(SKILL_SCRIPTS / "build_foreground_timeline.py"), str(root), str(timeline_path), "--duration-ms", str(duration_ms)], check=True)
    timeline = load(timeline_path)
    timeline["segments"] = apply_cover_visibility_overrides(
        timeline["segments"], presentation["foreground"].get("coverVisibilityOverrides")
    )
    renderer = ForegroundRenderer(root, width, height)
    state_files: dict[tuple, Path] = {}
    concat_lines = []
    for segment in timeline["segments"]:
        key = (segment["kind"], segment.get("frameId"), segment.get("activePartIndex"), segment["coverVisible"])
        if key not in state_files:
            path = foreground_dir / f"state-{len(state_files):05}.png"
            # State paths are deterministic for a run id.  Reusing a fully
            # written existing state makes an interrupted long render
            # resumable without painting onto a cumulative canvas.
            if not path.exists():
                renderer.render(
                    segment.get("frameId"),
                    segment.get("activePartIndex") if segment["kind"] == "active" else None,
                    path,
                    cover_only=segment["kind"] == "cover",
                    cover_visible=segment["coverVisible"],
                )
            state_files[key] = path
        concat_lines += [f"file '{state_files[key].as_posix()}'", f"duration {(segment['endMs']-segment['startMs'])/1000:.6f}"]
    concat_lines.append(f"file '{state_files[key].as_posix()}'")
    concat_path = run / "foreground.concat.txt"; concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8", newline="\n")

    background_args, background_filter, background_count = background_inputs_and_filter(root, scenes, width, height, duration_ms)
    command = ["ffmpeg", "-y", "-v", "error", *background_args, "-f", "concat", "-safe", "0", "-i", str(concat_path)]
    foreground_index = background_count; overlay = presentation.get("floatingOverlay", {}); overlay_on = bool(overlay.get("enabled"))
    spectrum_path = run / "foobar-spectrum.mov"
    if overlay_on:
        subprocess.run([sys.executable, str(SKILL_SCRIPTS / "render_foobar_spectrum.py"), str(music), str(project / "palette.json"), str(spectrum_path), "--duration-ms", str(duration_ms), "--offset-ms", str(offset)], check=True)
        command += ["-i", str(spectrum_path)]; spectrum_index = foreground_index + 1
    if offset >= 0:
        command += ["-itsoffset", f"{offset/1000:.6f}", "-i", str(music)]
    else:
        command += ["-ss", f"{-offset/1000:.6f}", "-i", str(music)]
    music_index = foreground_index + 1 + int(overlay_on)
    filters = [background_filter, f"[{foreground_index}:v]fps=30,format=rgba,setpts=PTS-STARTPTS[foreground]", "[background][foreground]overlay=0:0:format=auto[learning]"]
    if overlay_on:
        overlay_template = load(project / "templates" / "overlay.json")["render"]
        x = round(overlay_template["xPxAt1920x1080"] * width / 1920); y = round(overlay_template["yPxAt1920x1080"] * height / 1080)
        filters += [f"[{spectrum_index}:v]fps=30,format=rgba,setpts=PTS-STARTPTS[spectrum]", f"[learning][spectrum]overlay={x}:{y}:format=auto,fps=30,format=yuv420p[video]"]
    else:
        filters += ["[learning]fps=30,format=yuv420p[video]"]
    slug = manifest["slug"]; filename = args.output_name or f"{slug}--{canvas.get('name','canvas')}--{args.run_id}.mkv"
    candidate = run / filename
    command += ["-filter_complex", ";".join(filters), "-map", "[video]", "-map", f"{music_index}:a:0", "-t", f"{duration_ms/1000:.6f}", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-vsync", "cfr", "-c:a", "copy", "-progress", str(run / "ffmpeg-progress.txt"), str(candidate)]
    subprocess.run(command, check=True)
    write(run / "render-report.json", {
        "schemaVersion": 2, "candidate": str(candidate), "candidateSha256": sha(candidate),
        "activeHashes": {"inputManifest": sha(project / "input-manifest.json"), "presentation": sha(project / "presentation.json"), "sceneTimeline": sha(project / "scene-timeline.json"), "frames": sha(project / "frames.json")},
        "layers": ["background", "foreground", "floatingOverlay" if overlay_on else "floatingOverlay-disabled"],
        "scenes": scenes, "foregroundDefaultMode": presentation["foreground"]["defaultMode"],
        "durationMs": duration_ms, "offsetMs": offset, "audioCodecPolicy": "stream-copy", "foregroundTimeline": timeline["summary"],
    })
    print(json.dumps({"candidate": str(candidate), "durationMs": duration_ms, "states": len(state_files), "spectrum": overlay_on}, ensure_ascii=False))


if __name__ == "__main__":
    main()
