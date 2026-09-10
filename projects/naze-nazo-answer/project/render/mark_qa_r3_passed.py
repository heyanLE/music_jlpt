"""Record the visual QA decision for the current r3 candidate."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "project" / "qa" / "naze-approved-r3-qmts-dedupe" / "qa-report.json"

report = json.loads(REPORT.read_text(encoding="utf-8"))
report["result"] = "passed"
report["visualInspection"] = {
    "inspectedAt": datetime.now(timezone.utc).isoformat(),
    "findings": [
        "Current QMTS full-line Chinese is visible and the reviewed Japanese, readings and cards are preserved.",
        "Exact duplicate cards are absent within the inspected sentences; cards remain one translucent horizontal row.",
        "Foreground text has black outline; card meanings wrap only in the middle field; no clipping was observed.",
        "The transparent bottom spectrum persists through the background-only transition to cover Gaussian.",
        "Candidate probe confirms 1920x1080 CFR 30 H.264 plus stream-copied 96 kHz/24-bit FLAC audio."
    ]
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"report": str(REPORT), "result": "passed"}, ensure_ascii=False))
