"""Render every merged frame and report fixed-template layout failures."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "project"
sys.path.insert(0, r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts")
from render_video import ForegroundRenderer

frames = json.loads((P / "frames.json").read_text(encoding="utf-8"))["frames"]
renderer = ForegroundRenderer(ROOT, 1920, 1080)
out = P / "qa/merged-layout/states"; out.mkdir(parents=True, exist_ok=True)
failures = []
for frame in frames:
    try: renderer.render(frame["id"], None, out / f"{frame['id']}.png")
    except Exception as error: failures.append({"frameId": frame["id"], "error": str(error)})
report = {
    "schemaVersion": 1, "stage": "post-merge", "result": "passed" if not failures else "failed",
    "frameCount": len(frames), "renderedFrameCount": len(frames) - len(failures),
    "highRiskFrames": ["l032", "l038", "l055", "l061"], "failures": failures,
}
(P / "qa/merged-layout-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
if failures: raise SystemExit(2)
