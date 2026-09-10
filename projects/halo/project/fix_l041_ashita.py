"""Apply the user-confirmed sung reading for both repeated 明日 lines."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
READING = "\u3042\u3057\u305f"
KATAKANA = "\u30a2\u30b7\u30bf"

for name in ("halo.frames.assisted.review.json",):
    path = ROOT / name
    data = json.loads(path.read_text(encoding="utf-8"))
    for frame_id in ("l020", "l041"):
        frame = next(item for item in data["frames"] if item["id"] == frame_id)
        card = frame["grammarCards"][0]
        card["reading"] = KATAKANA
        card["romaji"] = "ashita"
        frame["caption"]["furigana"][0]["reading"] = KATAKANA
        frame["caption"]["furigana"][0]["romaji"] = "ashita"
        frame["caption"]["romaji"] = "ashita ninareba mata"
        frame["analysisStatus"] = "human-corrected-ashita"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("Updated l020 and l041 to the sung reading: ashita")
