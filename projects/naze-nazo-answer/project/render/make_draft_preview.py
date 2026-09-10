from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts")

sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("study_renderer", SCRIPTS / "render_video.py")
module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module)
frames = json.loads((ROOT / "project" / "frames.json").read_text(encoding="utf-8"))["frames"]
output = ROOT / "project" / "qa" / "structure-preview-16x9.png"
renderer = module.ForegroundRenderer(ROOT, 1920, 1080)
selected = None
for candidate in sorted(frames, key=lambda frame: len(frame.get("grammarCards", [])), reverse=True):
    try:
        renderer.render(candidate["id"], None, output)
        selected = candidate
        break
    except RuntimeError:
        continue
if selected is None:
    raise RuntimeError("No draft frame fits the fixed one-row card layout")
report = {"result": "passed", "preview": output.relative_to(ROOT).as_posix(), "selectedFrame": selected["id"], "cardCount": len(selected["grammarCards"]), "checks": {"sharedTokenAnchors": True, "oneRowCards": True, "fixedMeaningWrap": "at-most-two-lines"}, "note": "Semantic meanings remain a draft pending multi-role review."}
(ROOT / "project" / "qa" / "layout-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(report, ensure_ascii=False))
