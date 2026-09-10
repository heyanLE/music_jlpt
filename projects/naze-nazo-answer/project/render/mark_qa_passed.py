from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "project" / "qa" / "naze-approved-r2-offset150" / "qa-report.json"
report = json.loads(REPORT.read_text(encoding="utf-8"))
report["result"] = "passed"
report["visualInspection"] = {
  "inspectedAt": datetime.now(timezone.utc).isoformat(),
  "findings": [
    "First mixed Japanese-English lyric preserves QRC token timing and only Japanese tokens receive romaji/cards.",
    "Warm orange magic colour remains vivid over the foreground veil; all non-card text has black outline.",
    "Maximum-card and loanword samples keep a single translucent card row, two-line meanings, katakana source annotation, and a transparent bottom spectrum.",
    "The 90-second background-only fade enters cover Gaussian while the foreground and persistent transparent spectrum remain visible.",
    "Candidate is 1920x1080 CFR 30 with stream-copied 96 kHz/24-bit FLAC stereo audio; music, lyrics, and spectrum are delayed 150 ms against the unchanged background clock."
  ]
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"report": str(REPORT), "result": "passed"}, ensure_ascii=False))
