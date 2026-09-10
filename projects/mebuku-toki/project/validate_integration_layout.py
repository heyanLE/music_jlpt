#!/usr/bin/env python3
"""Validate the integrated proposal in memory; never modify frames.json."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    data = load(PROJECT / "frames.json")
    report = load(PROJECT / "review" / "integration-report.json")
    frames = {frame["id"]: copy.deepcopy(frame) for frame in data["frames"]}
    for change in report["recommendedProposalSet"]["changes"]:
        frame = frames[change["frameId"]]
        field = change["field"]
        if field == "grammarCards":
            frame["grammarCards"] = copy.deepcopy(change["new"])
        elif field.startswith("caption."):
            frame["caption"][field.split(".", 1)[1]] = copy.deepcopy(change["new"])
        else:
            raise RuntimeError(f"Unsupported integrated field: {field}")

    failures = []
    for frame in frames.values():
        for card in frame["grammarCards"]:
            if bool(card.get("zhMeaning")) == bool(card.get("functionZh")):
                failures.append({"frameId": frame["id"], "token": card.get("token"), "error": "meaning/function invariant"})
            if not card.get("grammarStructureZh"):
                failures.append({"frameId": frame["id"], "token": card.get("token"), "error": "missing grammarStructureZh"})

    renderer_path = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts\render_video.py")
    sys.path.insert(0, str(renderer_path.parent))
    spec = importlib.util.spec_from_file_location("study_render_video_integration", renderer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    renderer = module.ForegroundRenderer(ROOT, 1920, 1080)
    renderer.frames = frames
    output_dir = PROJECT / "qa" / "integration-previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    for frame_id in frames:
        try:
            renderer.render(frame_id, None, output_dir / f"{frame_id}.png")
        except Exception as error:
            failures.append({"frameId": frame_id, "error": str(error)})

    repeated = {}
    for frame in frames.values():
        repeated.setdefault(frame["caption"]["japanese"], []).append(frame)
    repeat_failures = []
    for japanese, group in repeated.items():
        if len(group) < 2:
            continue
        first = group[0]
        for other in group[1:]:
            if first["grammarCards"] != other["grammarCards"] or first["caption"]["translationZh"] != other["caption"]["translationZh"]:
                repeat_failures.append({"japanese": japanese, "frameIds": [item["id"] for item in group]})
    failures.extend({"error": "repeated-line inconsistency", **item} for item in repeat_failures)

    result = {
        "schemaVersion": 1,
        "result": "passed" if not failures else "failed",
        "framesChecked": len(frames),
        "cardCount": sum(len(frame["grammarCards"]) for frame in frames.values()),
        "checks": {
            "allFieldsInvariant": not any(item.get("error") in ("meaning/function invariant", "missing grammarStructureZh") for item in failures),
            "allFramesRenderAtFixedLayout": not any("exceeds" in item.get("error", "") or "fit" in item.get("error", "") for item in failures),
            "repeatedLinesConsistent": not repeat_failures,
            "framesJsonModified": False,
        },
        "failures": failures,
    }
    write(PROJECT / "qa" / "integration-layout-report.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
