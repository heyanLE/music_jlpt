"""Code-native single-frame layout experiment; never changes production inputs."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
SKILL = Path('C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts')
sys.path.insert(0, str(SKILL))
from render_video import ForegroundRenderer, load


def extract(source: Path, seconds: float, output: Path, video_filter: str = '') -> None:
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{seconds:.6f}', '-i', str(source)]
    if video_filter:
        command += ['-vf', video_filter]
    subprocess.run(command + ['-frames:v', '1', str(output)], check=True)


def main() -> None:
    frames_path = ROOT / 'project/frames.json'
    original_hash = hashlib.sha256(frames_path.read_bytes()).hexdigest()
    frames = load(frames_path)['frames']
    timeline = load(ROOT / 'project/work/episode-intro-corrected-r2/16x9/foreground-timeline.json')
    timestamp = 44000
    state = next(s for s in timeline['segments'] if s['startMs'] <= timestamp < s['endMs'])
    current_index = next(i for i, f in enumerate(frames) if f['id'] == state['frameId'])
    next_frame = frames[current_index + 1]
    renderer = ForegroundRenderer(ROOT, 1920, 1080)
    foreground_path = WORK / 'foreground-without-cover.png'
    renderer.render(state['frameId'], state.get('activePartIndex'), foreground_path, cover_visible=False)
    foreground = Image.open(foreground_path).convert('RGBA')

    # Native template extension: add a top preview band and move the original cover.
    preview = Image.new('RGBA', (1920, 1080))
    draw = ImageDraw.Draw(preview)
    draw.rounded_rectangle((350, 35, 1825, 255), radius=20, fill=(0, 0, 0, 72))
    preview.alpha_composite(renderer.cover.resize((220, 220), Image.Resampling.LANCZOS), (95, 35))
    renderer.outlined(draw, (380, 42), '下一句', renderer.font(23), (245, 245, 245, 255), 2)

    text = next_frame['caption']['japanese']
    fonts = {'japanese': renderer.font(54), 'romaji': renderer.font(34), 'ruby': renderer.font(28)}
    cards = next_frame['grammarCards']
    cells = []
    cursor = 0
    for card in cards:
        token = card['token']
        start = text.find(token, cursor)
        assert start >= 0 and not text[cursor:start].strip(), (token, cursor, start)
        end = start + len(token)
        jp_width = draw.textlength(token, font=fonts['japanese'])
        ro_width = draw.textlength(card.get('romaji', ''), font=fonts['romaji'])
        cells.append({'card': card, 'start': start, 'end': end, 'jpWidth': jp_width, 'romajiWidth': ro_width, 'width': max(jp_width, ro_width)})
        cursor = end
    assert not text[cursor:].strip()
    gap = 40
    total = sum(c['width'] for c in cells) + gap * (len(cells) - 1)
    assert total <= 1385, 'Preview line needs a separate long-line layout'
    x = 395 + (1385 - total) / 2
    anchors = []
    for cell in cells:
        card = cell['card']
        token_x = x + (cell['width'] - cell['jpWidth']) / 2
        renderer.outlined(draw, (token_x, 105), card['token'], fonts['japanese'], 'white', 3)
        renderer.outlined(draw, (x + (cell['width'] - cell['romajiWidth']) / 2, 184), card.get('romaji', ''), fonts['romaji'], 'white', 2)
        for ruby in next_frame['caption'].get('furigana', []):
            start, end = int(ruby['start']), int(ruby['end'])
            if cell['start'] <= start and end <= cell['end']:
                assert text[start:end] == ruby['base']
                ruby_x = token_x + draw.textlength(text[cell['start']:start], font=fonts['japanese'])
                renderer.outlined(draw, (ruby_x, 73), ruby['reading'], fonts['ruby'], 'white', 2)
                anchors.append({'base': ruby['base'], 'reading': ruby['reading'], 'x': ruby_x})
        x += cell['width'] + gap
    assert len(anchors) == len(next_frame['caption'].get('furigana', []))
    foreground.alpha_composite(preview)
    foreground.save(WORK / 'preview-foreground.png')

    # Rebuild from the same background and spectrum assets, not an AI-painted screenshot.
    # The 21.75525-second intro occupies 653 CFR30 frames in the approved composite.
    source_frame = timestamp * 30 // 1000 - 653
    extract(ROOT / 'source/background.mp4', source_frame / 30, WORK / 'background.png',
            'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black')
    extract(ROOT / 'project/work/episode-intro-corrected-r2/16x9/foobar-spectrum.mov', timestamp / 1000, WORK / 'spectrum.png', 'format=rgba')
    image = Image.open(WORK / 'background.png').convert('RGBA')
    image.alpha_composite(foreground)
    overlay = load(ROOT / 'project/templates/overlay.json')['render']
    image.alpha_composite(Image.open(WORK / 'spectrum.png').convert('RGBA'),
                          (overlay['xPxAt1920x1080'], overlay['yPxAt1920x1080']))
    output = ROOT / 'deliverables/review/next-line-preview-a--00m44s.png'
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert('RGB').save(output)
    assert hashlib.sha256(frames_path.read_bytes()).hexdigest() == original_hash
    report = {'kind': 'static-layout-experiment-only', 'timestampMs': timestamp,
              'currentFrame': state['frameId'], 'nextFrame': next_frame['id'],
              'framesSha256': original_hash, 'productionFilesModified': False,
              'nextLineText': text, 'rubyAnchors': anchors, 'output': str(output)}
    (WORK / 'preview-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
