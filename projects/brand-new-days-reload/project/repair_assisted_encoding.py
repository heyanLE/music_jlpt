"""Repair UTF-8 text that was displayed through a GBK shell during proposal import."""
import json
from pathlib import Path

PATH = Path(__file__).parent / "frames.assisted.review.json"

def repair(value):
    if isinstance(value, str):
        try:
            candidate = value.encode("gbk").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return value
        # Only accept a conversion that materially reduces suspicious CJK mojibake.
        return candidate
    if isinstance(value, list): return [repair(item) for item in value]
    if isinstance(value, dict): return {key: repair(item) for key, item in value.items()}
    return value

data = json.loads(PATH.read_text(encoding="utf-8"))
PATH.write_text(json.dumps(repair(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("repaired")
