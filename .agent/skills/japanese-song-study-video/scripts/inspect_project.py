#!/usr/bin/env python3
"""Read-only recovery summary. Does not authorize work or mutate project state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify_render_gate import load, sha, verify_review_gate, verify_render_gate


def inspect(root: Path, renderer: Path | None = None) -> dict:
    root = root.resolve()
    project = root / "project"
    result = {"schemaVersion": 1, "projectRoot": str(root), "readOnly": True,
              "artifacts": {}, "issues": [], "checksNotPerformed": [
                  "full media hashes", "visual QA", "unimported human Markdown edits",
                  "custom renderer internal dependencies"]}

    def read(relative: str) -> dict:
        path = root / relative
        record = {"exists": path.is_file()}
        result["artifacts"][relative] = record
        if not path.is_file():
            return {}
        record["sha256"] = sha(path)
        try:
            return load(path)
        except (ValueError, OSError) as exc:
            result["issues"].append(str(exc))
            return {}

    manifest = read("project/input-manifest.json")
    state = read("project/build-state.json")
    presentation = read("project/presentation.json")
    scene = read("project/scene-timeline.json")
    frames = read("project/frames.json")
    decision = read("project/review/review-decision.json")
    authorization = read("project/render-authorization.json")
    plan = read("project/render/render-plan.json")
    final = read("project/final-manifest.json")
    result.update({"declaredStage": state.get("stage"), "preset": manifest.get("pipelinePreset"),
                   "outputs": manifest.get("outputs", []), "presentation": presentation,
                   "sceneCount": len(scene.get("segments", [])),
                   "frameCount": len(frames.get("frames", [])),
                   "contentDecision": {key: decision.get(key) for key in ("content", "scope", "userWording")},
                   "renderAuthorization": {key: authorization.get(key) for key in ("renderAuthorized", "userWording", "authorizationText", "authorization")},
                   "renderPlan": {"runId": plan.get("runId"), "entryPoint": plan.get("entryPoint") or plan.get("renderer"), "outputs": plan.get("outputs") or plan.get("canvases"), "state": plan.get("state")},
                   "finalManifest": final})

    try:
        verify_review_gate(root)
        result["reviewGate"] = {"status": "passed"}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result["reviewGate"] = {"status": "not-current", "reason": str(exc)}
    if renderer is None:
        result["renderGate"] = {"status": "not-checked", "reason": "Pass --renderer with the recorded entrypoint; do not guess for custom projects."}
    else:
        try:
            verify_render_gate(root, renderer.resolve())
            result["renderGate"] = {"status": "passed", "renderer": str(renderer.resolve())}
        except (ValueError, OSError, KeyError, TypeError) as exc:
            result["renderGate"] = {"status": "not-current", "reason": str(exc)}

    # Existence is useful for recovery, but does not certify a prior output.
    if final.get("output"):
        final_path = (root / final["output"]).resolve()
        try:
            final_path.relative_to(root)
            result["finalOutputExists"] = final_path.is_file()
        except ValueError:
            result["issues"].append("Final manifest output is outside project root")
    result["reviewDocuments"] = [str(p.relative_to(root)) for p in sorted((root / "deliverables" / "review").glob("*.md"))]
    result["qaReports"] = [str(p.relative_to(root)) for p in sorted((project / "qa").glob("**/qa-report.json"))]
    if not manifest or not scene or not presentation:
        phase = "01-inputs"
    elif not (project / "timing" / "decode-report.json").exists() or not (project / "palette.json").exists():
        phase = "02-project-setup"
    elif not frames.get("frames"):
        phase = "03-card-draft"
    elif result["reviewGate"]["status"] != "passed":
        phase = "04-assisted-review"
    else:
        phase = "05-render"
    result["nextPhaseToInspect"] = phase
    result["guidance"] = "Check the current request and listed artifacts before executing. Existing finals may be delivered without rerender; missing/stale evidence is not permission to recreate approval. This summary does not import Markdown or certify setup/draft quality."
    return result


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--renderer", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.project_root, args.renderer), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
