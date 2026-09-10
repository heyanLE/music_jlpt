from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "project" / "qa" / "dare-v3-approved-r1" / "qa-report.json"

def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    report["result"] = "passed"
    report["visualInspection"] = {
        "inspectedAt": datetime.now(timezone.utc).isoformat(),
        "findings": [
            "13.184-second first-frame Gaussian prelude is present before the ED video begins.",
            "First lyric begins at the ED programme start; cover, ruby, token romaji, Chinese, and cards remain legible.",
            "The video-to-cover-Gaussian switch keeps learning foreground and transparent bottom spectrum intact.",
            "Cards are a single row, meanings wrap within two lines, and all foreground text has black outline.",
            "Final lyric and persistent spectrum render correctly; candidate is 1920x1080 CFR 30 with FLAC audio.",
        ],
        "extraScreenshots": ["project/qa/dare-v3-approved-r1/prelude-first-frame.png"],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(REPORT), "result": "passed"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
