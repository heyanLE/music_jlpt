"""Generate isolated synthetic layout QA images, without music or video encoding."""
import argparse
import json
from pathlib import Path
import tempfile

from PIL import Image
from foreground_options import configure_options
from render_video import ForegroundRenderer


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("output_dir", type=Path); args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); project = root / "project"; (project / "timing").mkdir(parents=True)
        def write(name, doc): (project / name).write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        Image.new("RGB", (220, 220), "#4576b5").save(root / "cover.png")
        write("input-manifest.json", {"cover": {"asset": "cover.png"}})
        write("palette.json", {"accent": "#264f85", "activeTint": "#56bbff", "cardFill": {"alpha": .75}})
        frames = []
        for i, (word, reading, romaji, meaning) in enumerate((("風", "かぜ", "kaze", "风"), ("声", "こえ", "koe", "声音"), ("光", "ひかり", "hikari", "光芒"))):
            frames.append({"id": f"l{i}", "startMs": 5000 + i * 4000, "endMs": 7000 + i * 4000,
                "caption": {"japanese": word + "を感じる", "translationZh": "感受" + meaning,
                    "furigana": [{"base": word, "reading": reading, "baseStart": 0}, {"base": "感", "reading": "かん", "baseStart": 2}]},
                "grammarCards": [{"token": word, "romaji": romaji, "zhMeaning": meaning, "grammarStructureZh": "名词"},
                    {"token": "を", "romaji": "o", "functionZh": "动作对象", "grammarStructureZh": "格助词"},
                    {"token": "感じる", "romaji": "kanjiru", "zhMeaning": "感受", "grammarStructureZh": "动词"}]})
        write("frames.json", {"frames": frames})
        write("timing/qm.json", {"lines": [{"text": f["caption"]["japanese"], "startMs": f["startMs"], "endMs": f["endMs"], "parts": [{"text": card["token"]} for card in f["grammarCards"]]} for f in frames]})
        for enabled in (False, True):
            options = configure_options(None, "on" if enabled else "off", "on" if enabled else "off")
            write("presentation.json", {"foreground": {**options, "veil": {"opacity": .28}, "textOutline": {"enabled": True}}})
            for width, height, label in ((1920, 1080, "16x9"), (1440, 1080, "4x3")):
                renderer = ForegroundRenderer(root, width, height)
                def save(name, foreground):
                    composite = Image.new("RGBA", (width, height), "#536575"); composite.alpha_composite(foreground)
                    composite.convert("RGB").save(args.output_dir / f"{label}-{name}.png")
                save("on" if enabled else "off", renderer.render("l1", 0, None))
                if enabled:
                    save("countdown", renderer.render("l0", None, None, countdown_value=3))
                    blank = renderer.render(None, None, None, countdown_value=2)
                    assert blank.getbbox() is not None and blank.getpixel((0, height - 1))[3] == 0
                    save("countdown-hidden-prelude", blank)
        # Raw mixed-language order and repeated-token anchors remain intact.
        mixed = {"id": "mixed", "startMs": 17000, "endMs": 20000,
            "caption": {"japanese": "光 my light 光", "translationZh": "光，我的光，光", "furigana": [{"base": "光", "reading": "ひかり", "baseStart": 0}, {"base": "光", "reading": "ひかり", "baseStart": 11}]},
            "grammarCards": [{"token": "光", "romaji": "hikari", "zhMeaning": "光芒", "grammarStructureZh": "名词"}, {"token": "光", "romaji": "hikari", "zhMeaning": "光芒", "grammarStructureZh": "名词"}]}
        frames.append(mixed)
        frames.append({"id": "english", "startMs": 21000, "endMs": 23000, "caption": {"japanese": "My light stays here", "translationZh": "我的光留在这里", "furigana": []}, "grammarCards": []})
        write("frames.json", {"frames": frames})
        write("timing/qm.json", {"lines": [{"text": f["caption"]["japanese"], "startMs": f["startMs"], "endMs": f["endMs"], "parts": [{"text": f["caption"]["japanese"]}]} for f in frames]})
        write("presentation.json", {"foreground": {**configure_options(None), "veil": {"opacity": .28}}})
        for width, height, label in ((1920, 1080, "16x9"), (1440, 1080, "4x3")):
            renderer = ForegroundRenderer(root, width, height)
            for frame_id in ("mixed", "english"):
                image = renderer.render(frame_id, 0, None)
                composite = Image.new("RGBA", (width, height), "#536575"); composite.alpha_composite(image)
                composite.convert("RGB").save(args.output_dir / f"{label}-{frame_id}.png")
    print(str(args.output_dir.resolve()))


if __name__ == "__main__": main()
