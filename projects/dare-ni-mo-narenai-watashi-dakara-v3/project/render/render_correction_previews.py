from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts")
FRAME_IDS = ("l011", "l037", "l043", "l044")


def main() -> None:
    sys.path.insert(0, str(SKILL_SCRIPTS))
    spec = importlib.util.spec_from_file_location("study_renderer", SKILL_SCRIPTS / "render_video.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    output_dir = ROOT / "project" / "qa" / "correction-20260902" / "after"
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = module.ForegroundRenderer(ROOT, 1920, 1080)
    outputs = []
    for frame_id in FRAME_IDS:
        output = output_dir / f"{frame_id}.png"
        renderer.render(frame_id, None, output)
        outputs.append(output.relative_to(ROOT).as_posix())
    report = {
        "schemaVersion": 2,
        "result": "pending-visual-review",
        "frameIds": list(FRAME_IDS),
        "outputs": outputs,
    }
    report_path = output_dir / "preview-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
