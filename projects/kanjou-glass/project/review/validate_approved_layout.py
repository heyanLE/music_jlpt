from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
SKILL = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    document = load(PROJECT / "frames.json")
    frames = {frame["id"]: frame for frame in document["frames"]}
    failures = []
    for frame in frames.values():
        for card in frame.get("grammarCards", []):
            if bool(card.get("zhMeaning")) == bool(card.get("functionZh")):
                failures.append({"frameId": frame["id"], "token": card.get("token"), "error": "meaning/function invariant"})
            if not card.get("grammarStructureZh"):
                failures.append({"frameId": frame["id"], "token": card.get("token"), "error": "missing grammarStructureZh"})

    renderer_path = SKILL / "scripts" / "render_video.py"
    sys.path.insert(0, str(renderer_path.parent))
    spec = importlib.util.spec_from_file_location("study_render_video_approved", renderer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    renderer = module.ForegroundRenderer(ROOT, 1920, 1080)
    output_dir = PROJECT / "qa" / "approved-layout" / "states"
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame_id in frames:
        try:
            renderer.render(frame_id, None, output_dir / f"{frame_id}.png", cover_visible=True)
        except Exception as error:
            failures.append({"frameId": frame_id, "error": str(error)})

    repeated = {}
    for frame in frames.values():
        repeated.setdefault(frame["caption"]["japanese"], []).append(frame)
    repeat_failures = []
    for japanese, group in repeated.items():
        if len(group) > 1 and any(group[0]["grammarCards"] != other["grammarCards"] for other in group[1:]):
            repeat_failures.append({"japanese": japanese, "frameIds": [item["id"] for item in group]})
    failures.extend({"error": "repeated-card inconsistency", **item} for item in repeat_failures)

    report = {
        "schemaVersion": 1,
        "result": "passed" if not failures else "failed",
        "framesChecked": len(frames),
        "cardCount": sum(len(frame.get("grammarCards", [])) for frame in frames.values()),
        "checks": {
            "allFieldsInvariant": not any(item.get("error") in ("meaning/function invariant", "missing grammarStructureZh") for item in failures),
            "allFramesRenderAtFixedLayout": not any(item.get("frameId") and item.get("error") not in ("meaning/function invariant", "missing grammarStructureZh") for item in failures),
            "repeatedCardBundlesConsistent": not repeat_failures,
        },
        "failures": failures,
    }
    write(PROJECT / "qa" / "approved-layout-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
