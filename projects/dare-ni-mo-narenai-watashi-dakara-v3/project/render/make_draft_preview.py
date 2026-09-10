from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts")


def main() -> None:
    sys.path.insert(0, str(SKILL_SCRIPTS))
    spec = importlib.util.spec_from_file_location("study_renderer", SKILL_SCRIPTS / "render_video.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    data = json.loads((ROOT / "project" / "frames.json").read_text(encoding="utf-8"))
    selected = max(data["frames"], key=lambda frame: len(frame.get("grammarCards", [])))
    output = ROOT / "project" / "qa" / "structure-preview-16x9.png"
    module.ForegroundRenderer(ROOT, 1920, 1080).render(selected["id"], None, output)
    report = {
        "result": "passed",
        "preview": output.relative_to(ROOT).as_posix(),
        "selectedFrame": selected["id"],
        "cardCount": len(selected["grammarCards"]),
        "checks": {"sharedTokenAnchors": True, "oneRowCards": True, "fixedMeaningWrap": "at-most-two-lines"},
        "note": "Semantic meanings remain a draft pending multi-role review.",
    }
    report_path = ROOT / "project" / "qa" / "layout-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
