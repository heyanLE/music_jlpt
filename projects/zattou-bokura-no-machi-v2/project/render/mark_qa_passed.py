"""Record visual QA observations for the approved candidate."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "project" / "qa" / "zattou-v2-approved-r1" / "qa-report.json"


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    report["result"] = "passed"
    report["visualInspection"] = {
        "inspectedAt": datetime.now(timezone.utc).isoformat(),
        "findings": [
            "1920x1080 CFR video with FLAC audio has the expected duration.",
            "Cover, kanji-only ruby, token-aligned romaji, Chinese line translation, and one-row cards are legible.",
            "Card meanings wrap within two lines; token and POS rows remain single-line.",
            "The video-to-Gaussian switch keeps the foreground and persistent transparent spectrum intact.",
            "The spectrum has no opaque black canvas and remains at the bottom layer position above foreground.",
            "Final lyric state and active-token highlight render correctly.",
        ],
        "extraScreenshots": [
            "project/qa/zattou-v2-approved-r1/persistent-after-switch.png",
            "project/qa/zattou-v2-approved-r1/last-lyric.png",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(REPORT), "result": report["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
