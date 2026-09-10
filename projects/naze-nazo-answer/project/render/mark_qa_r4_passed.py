"""Record QA for the l019-corrected r4 candidate."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "project" / "qa" / "naze-approved-r4-l019-gomen" / "qa-report.json"

report = json.loads(REPORT.read_text(encoding="utf-8"))
report["result"] = "passed"
report["visualInspection"] = {
    "inspectedAt": datetime.now(timezone.utc).isoformat(),
    "findings": [
        "l019 displays the user-corrected lyric ending ごめん with no trailing く(＿) fragment.",
        "l019 kanji annotations, token highlight, one-row cards and current QMTS Chinese remain readable and aligned.",
        "Spectrum stays transparent and persistent; background/foreground three-layer composition is intact.",
        "Candidate probe confirms 1920x1080 CFR 30 H.264 plus stream-copied 96 kHz/24-bit FLAC audio."
    ]
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"report": str(REPORT), "result": "passed"}, ensure_ascii=False))
