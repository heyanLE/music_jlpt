from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "project" / "frames.json"


def main() -> None:
    data = json.loads(FRAMES.read_text(encoding="utf-8"))
    removed = {"l001", "l002", "l003", "l004", "l005"}
    data["frames"] = [frame for frame in data["frames"] if frame["id"] not in removed]
    data["metadataPolicy"] = "QRC title, artist, album and credits rows l001-l005 excluded from display"
    FRAMES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"removed": sorted(removed), "remaining": len(data["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
