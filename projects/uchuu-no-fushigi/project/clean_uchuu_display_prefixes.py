"""Remove accidental display-label punctuation from reviewed Uchu card values."""
import json
from pathlib import Path

PATH = Path(__file__).parent / "uchuu.frames.approved.json"
data = json.loads(PATH.read_text(encoding="utf-8"))
changed = 0
for frame in data["frames"]:
    for card in frame.get("grammarCards", []):
        for key in ("zhMeaning", "functionZh", "posZh"):
            value = card.get(key)
            if isinstance(value, str):
                cleaned = value.lstrip("：: ")
                if cleaned != value:
                    card[key] = cleaned
                    changed += 1
PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Removed {changed} accidental display prefixes.")
