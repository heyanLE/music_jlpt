#!/usr/bin/env python3
"""Common mandatory review and render-authorization gate for every renderer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath


REQUIRED_ROLES = {"lexical", "grammar", "translation"}


def load(path: Path) -> dict:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"BOM is forbidden: {path}")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Top level must be object: {path}")
    return data


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    return path


def inside(root: Path, value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside project root: {path}") from exc
    return required_file(path, label)


def verify_review_gate(root: Path) -> dict:
    root = root.resolve(); project = root / "project"
    frames_path = required_file(project / "frames.json", "frames.json")
    audit_path = required_file(project / "review" / "assisted-review-audit.json", "sealed multi-agent audit")
    merge_path = required_file(project / "review" / "merge-log.json", "review merge log")
    decision_path = required_file(project / "review" / "review-decision.json", "explicit content decision")
    audit = load(audit_path)
    if audit.get("mode") != "mandatory-multi-agent" or audit.get("status") != "completed":
        raise ValueError("Mandatory multi-agent audit is incomplete")
    if set(audit.get("roles", [])) != REQUIRED_ROLES:
        raise ValueError("Audit must contain lexical, grammar, and translation roles")

    proposal_roles = set()
    for record in audit.get("proposalFiles", []):
        role = record.get("role")
        if role not in REQUIRED_ROLES:
            raise ValueError(f"Invalid sealed proposal role: {role}")
        path = inside(root, record.get("file", ""), f"{role} proposal")
        if record.get("sha256") != sha(path):
            raise ValueError(f"Sealed proposal changed after audit: {path}")
        declared_role = str(load(path).get("reviewRole", ""))
        if declared_role.split("-", 1)[0] != role:
            raise ValueError(f"Proposal role changed after audit: {path}")
        proposal_roles.add(role)
    if proposal_roles != REQUIRED_ROLES:
        raise ValueError("At least one sealed proposal file is required for each review role")

    integration_record = audit.get("integration", {})
    integration_path = inside(root, integration_record.get("file", ""), "integration report")
    if integration_record.get("sha256") != sha(integration_path):
        raise ValueError("Integration report changed after audit")
    integration = load(integration_path)
    if integration.get("reviewRole") != "integration" or integration.get("status") != "completed":
        raise ValueError("Independent integration pass is incomplete")

    frame_sha = sha(frames_path); merge = load(merge_path); decision = load(decision_path)
    if merge.get("framesAfterSha256") != frame_sha:
        raise ValueError("Merge log is stale for the current frames.json")
    if decision.get("content") != "approved" or decision.get("frameSha256") != frame_sha:
        raise ValueError("Explicit content approval is missing or stale")
    if not (decision.get("userWording") or decision.get("authorization")):
        raise ValueError("Content decision must preserve the user's verbatim approval wording")
    if decision.get("assistedReviewAuditSha256") != sha(audit_path):
        raise ValueError("Content decision is not bound to the assisted-review audit")
    if decision.get("mergeLogSha256") != sha(merge_path):
        raise ValueError("Content decision is not bound to the merge log")
    return {
        "auditPath": audit_path,
        "mergePath": merge_path,
        "decisionPath": decision_path,
        "frameSha256": frame_sha,
    }


def authorization_hash_paths(root: Path, renderer: Path, review: dict) -> dict[str, Path]:
    project, source = root / "project", root / "source"
    paths = {
        "inputManifestSha256": project / "input-manifest.json",
        "sourceManifestSha256": source / "source-manifest.json",
        "frameSha256": project / "frames.json",
        "paletteSha256": project / "palette.json",
        "presentationSha256": project / "presentation.json",
        "sceneSha256": project / "scene-timeline.json",
        "foregroundTemplateSha256": project / "templates" / "foreground.json",
        "overlayTemplateSha256": project / "templates" / "overlay.json",
        "rendererSha256": renderer,
        "assistedReviewAuditSha256": review["auditPath"],
        "mergeLogSha256": review["mergePath"],
        "reviewDecisionSha256": review["decisionPath"],
    }
    if renderer.resolve() == Path(__file__).with_name("render_video.py").resolve():
        for name in ("foreground_options.py", "build_foreground_timeline.py", "render_foobar_spectrum.py", "verify_render_gate.py", "runtime_font.py"):
            paths["rendererDependency:" + name] = Path(__file__).with_name(name)
    dependency_manifest = project / 'render' / 'renderer-dependencies.json'
    if dependency_manifest.is_file():
        paths['rendererDependencyManifestSha256'] = dependency_manifest
        entries = load(dependency_manifest).get('files')
        if not isinstance(entries, list) or not entries or not all(isinstance(x, str) for x in entries):
            raise ValueError('renderer-dependencies.json needs a nonempty files list')
        if len(set(entries)) != len(entries):
            raise ValueError('Duplicate renderer dependency')
        for value in entries:
            if Path(value).is_absolute() or PureWindowsPath(value).drive:
                raise ValueError('Renderer dependency paths must be project-relative')
            paths['projectRendererDependency:' + value] = inside(root, value, 'renderer dependency')
    return paths


def verify_render_gate(root: Path, renderer: Path) -> dict:
    root = root.resolve(); renderer = required_file(renderer.resolve(), "renderer")
    review = verify_review_gate(root)
    authorization_path = required_file(root / "project" / "render-authorization.json", "render authorization")
    authorization = load(authorization_path)
    if not authorization.get("renderAuthorized"):
        raise ValueError("Final render is not explicitly authorized")
    expected_paths = authorization_hash_paths(root, renderer, review)
    recorded_dependencies = {key for key in authorization if key == 'rendererDependencyManifestSha256' or key.startswith('projectRendererDependency:')}
    if recorded_dependencies - expected_paths.keys():
        raise ValueError('Previously authorized renderer dependency manifest or entries are missing')
    for key, path in expected_paths.items():
        required_file(path, key)
        if authorization.get(key) != sha(path):
            raise ValueError(f"Render authorization hash missing or stale: {key}")
    return {"authorizationPath": authorization_path, **review}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--renderer", type=Path, required=True)
    args = parser.parse_args()
    result = verify_render_gate(args.project_root.resolve(), args.renderer.resolve())
    print(json.dumps({"status": "PASS", "frameSha256": result["frameSha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
