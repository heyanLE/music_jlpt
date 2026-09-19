#!/usr/bin/env python3
"""Common mandatory review and render-authorization gate for every renderer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath


REQUIRED_ROLES = {"lexical", "grammar", "translation"}
MULTI_AGENT_MODE = "mandatory-multi-agent"
LEXICON_MODE = "lexicon-rag-targeted-online"
ONLINE_ROLES = {"online", "lexicon-online"}
# Wording that advances work but never authorizes content; mirrors authorize_render.py.
AMBIGUOUS_WORDINGS = {"继续", "开始", "可以", "下一步", "继续吧", "ok", "okay"}
# A rehearsal or test run must never be promotable as a real content decision.
PLACEHOLDER_MARKERS = ("REHEARSAL", "TEST-ONLY", "PLACEHOLDER", "DRYRUN", "DRY-RUN", "SANDBOX")


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


def audit_is_grounded(root: Path, merge: dict, audit: dict) -> bool:
    """Is the sealed draft hash a real ancestor of the current frames?

    The obvious check - "the merge started exactly where the review was sealed" -
    is wrong for projects that merged in several recorded rounds, where a later
    merge legitimately starts from an intermediate state. So the audit's base must
    match the current merge's input, the current frames, or the input of any merge
    log recorded in the project (or the normalized shell).
    """
    base = audit.get("baseFrameSha256")
    if not base:
        return False
    project = root / "project"
    frames_sha = sha(project / "frames.json")
    if base in (frames_sha, merge.get("framesBeforeSha256"), merge.get("framesAfterSha256")):
        return True
    for path in sorted((project / "review").glob("*merge-log*.json")):
        try:
            record = load(path)
        except (ValueError, OSError):
            continue
        if base in (record.get("framesBeforeSha256"), record.get("framesAfterSha256")):
            return True
    for name in ("frames-shell.json", "frames-draft.json"):
        candidate = project / "review" / name
        if candidate.is_file() and sha(candidate) == base:
            return True
    return False


def verify_review_gate(root: Path) -> dict:
    root = root.resolve(); project = root / "project"
    frames_path = required_file(project / "frames.json", "frames.json")
    audit_path = required_file(project / "review" / "assisted-review-audit.json", "sealed multi-agent audit")
    merge_path = required_file(project / "review" / "merge-log.json", "review merge log")
    decision_path = required_file(project / "review" / "review-decision.json", "explicit content decision")
    audit = load(audit_path)
    mode = audit.get("mode")
    if audit.get("status") != "completed":
        raise ValueError("Review audit is incomplete")
    if mode == MULTI_AGENT_MODE:
        verify_multi_agent_audit(root, audit)
    elif mode == LEXICON_MODE:
        verify_lexicon_audit(root, audit)
    else:
        raise ValueError(f"Unsupported review audit mode: {mode!r}")

    frame_sha = sha(frames_path); merge = load(merge_path); decision = load(decision_path)
    if merge.get("framesAfterSha256") != frame_sha:
        raise ValueError("Merge log is stale for the current frames.json")
    # The review was sealed against a draft that must be a real ancestor of the frames
    # being rendered. Without this binding a hand-written audit could be paired with
    # any merge log at all.
    if not audit_is_grounded(root, merge, audit):
        raise ValueError("Review audit is not sealed against any recorded ancestor of the current frames "
                         f"(audit base {str(audit.get('baseFrameSha256'))[:12]}, merge input "
                         f"{str(merge.get('framesBeforeSha256'))[:12]})")
    if decision.get("content") != "approved" or decision.get("frameSha256") != frame_sha:
        raise ValueError("Explicit content approval is missing or stale")
    wording = str(decision.get("userWording", "")).strip()
    if not wording:
        raise ValueError("Content decision must preserve the user's verbatim approval wording in userWording")
    if wording in AMBIGUOUS_WORDINGS:
        raise ValueError(f"Ambiguous wording is not a content decision: {wording!r}")
    if any(marker in wording.upper() for marker in PLACEHOLDER_MARKERS):
        raise ValueError(f"Placeholder wording is not a content decision: {wording!r}")
    if str(decision.get("wordingIsVerbatim", "")).lower() in ("false", "no"):
        raise ValueError("Content decision is marked as not verbatim")
    if decision.get("assistedReviewAuditSha256") != sha(audit_path):
        raise ValueError("Content decision is not bound to the assisted-review audit")
    if decision.get("mergeLogSha256") != sha(merge_path):
        raise ValueError("Content decision is not bound to the merge log")
    lexicon_source = root.parents[1] / "lexicon" / "lexicon.json"
    lexicon_document = load(lexicon_source) if lexicon_source.is_file() else {}
    return {
        "auditPath": audit_path,
        "mergePath": merge_path,
        "decisionPath": decision_path,
        "frameSha256": frame_sha,
        "reviewMode": mode,
        "lexiconSha256": audit.get("lexicon", {}).get("sha256") if mode == LEXICON_MODE else None,
        "lexiconContentSha256": lexicon_document.get("contentSha256"),
    }


def verify_multi_agent_audit(root: Path, audit: dict) -> None:
    """Three independent role proposals plus an integration pass (legacy projects)."""
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


def queued_unit_ids(queue: dict) -> set[str]:
    """Canonical identity of every unit the reviewer was asked to resolve."""
    return {
        f"{entry['frameId']}::{unit['text']}"
        for entry in queue.get("queue", [])
        for unit in entry.get("units", [])
    }


def verify_lexicon_audit(root: Path, audit: dict) -> None:
    """Lexicon RAG draft plus one targeted online review of the unresolved spans.

    Pinning hashes is not enough on its own: an internally consistent but empty
    review would otherwise satisfy the gate and remove the review obligation
    entirely. So the audit must also prove, from the sealed artifacts, that the
    review answered every queued unit exactly once, that it answered nothing else,
    and that the draft it describes is the draft on disk.
    """
    if audit.get("roles") != ["online"]:
        raise ValueError("Lexicon-mode audit must declare exactly the online review role")
    queue_record, review_record = audit.get("ragQueue", {}), audit.get("onlineReview", {})
    for record, label in ((queue_record, "RAG review queue"), (review_record, "online review")):
        path = inside(root, record.get("file", ""), label)
        if record.get("sha256") != sha(path):
            raise ValueError(f"{label} changed after the audit was sealed: {path}")
    queue = load(inside(root, queue_record.get("file", ""), "RAG review queue"))
    review = load(inside(root, review_record.get("file", ""), "online review"))

    lexicon_record = audit.get("lexicon", {})
    if not lexicon_record.get("sha256"):
        raise ValueError("Audit must pin the lexicon revision it was drafted from")
    if queue.get("lexiconSha256") != lexicon_record.get("sha256"):
        raise ValueError("Review queue and sealed lexicon revision disagree")
    if review.get("lexiconSha256") not in (None, lexicon_record.get("sha256")):
        raise ValueError("Online review and sealed lexicon revision disagree")
    if review.get("queueSha256") and review["queueSha256"] != sha(inside(root, queue_record.get("file", ""), "RAG review queue")):
        raise ValueError("Online review was produced against a different review queue")
    if str(review.get("reviewRole", "")) not in ONLINE_ROLES or review.get("status") != "completed":
        raise ValueError("Targeted online review is incomplete")

    # 1. Every queued unit must be answered, exactly once, and only queued units may be claimed.
    expected = queued_unit_ids(queue)
    changes = review.get("changes", review.get("proposals", []))
    answered: dict[str, int] = {}
    for change in changes:
        if not isinstance(change, dict):
            raise ValueError("Online review changes must be objects")
        frame_id = str(change.get("frameId", ""))
        unit_text = str(change.get("unit", change.get("text", "")))
        if not frame_id or not unit_text:
            raise ValueError(f"Online review change must name frameId and unit: {change!r}")
        if not str(change.get("resolution", change.get("new", ""))).strip():
            raise ValueError(f"Online review change must carry a resolution: {frame_id}::{unit_text}")
        unit_id = f"{frame_id}::{unit_text}"
        if unit_id not in expected:
            raise ValueError(f"Online review answered a unit that was never queued: {unit_id}")
        answered[unit_id] = answered.get(unit_id, 0) + 1
    missing = sorted(expected - set(answered))
    if missing:
        raise ValueError(f"Online review left {len(missing)} queued unit(s) unanswered, e.g. {missing[:3]}")
    repeated = sorted(unit_id for unit_id, count in answered.items() if count > 1)
    if repeated:
        raise ValueError(f"Online review answered the same unit more than once: {repeated[:3]}")

    # 2. The audit's declared coverage must match reality, and the draft must be non-empty.
    coverage = audit.get("coverage", {})
    totals = queue.get("totals", {})
    for key in ("frames", "reviewUnits"):
        if key in totals and coverage.get(key) != totals[key]:
            raise ValueError(f"Audit coverage.{key} ({coverage.get(key)}) disagrees with the sealed queue ({totals[key]})")
    if coverage.get("checkedUnits") not in (None, len(answered)):
        raise ValueError("Audit coverage.checkedUnits disagrees with the sealed review")
    frames_document = load(root / "project" / "frames.json")
    frame_ids = [frame.get("id") for frame in frames_document.get("frames", [])]
    card_count = sum(len(frame.get("grammarCards", [])) for frame in frames_document.get("frames", []))
    if coverage.get("frames") not in (None, len(frame_ids)):
        raise ValueError("Audit coverage.frames disagrees with frames.json")
    content = audit.get("content", {})
    # The card count is deliberately not compared here: the accepted merge may delete
    # cards (a merged card pair), while the audit describes the draft it sealed. The
    # draft's own non-emptiness is enforced at seal time.
    if content.get("frames") not in (None, len(frame_ids)):
        raise ValueError("Audit content.frames disagrees with frames.json")
    if card_count == 0 and not content.get("allRowsEnglish"):
        raise ValueError("A project with no cards must declare content.allRowsEnglish with a reason")
    for change in changes:
        if str(change.get("frameId")) not in frame_ids:
            raise ValueError(f"Online review references an unknown frame: {change.get('frameId')}")


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
    # A lexicon-drafted project is only reproducible against the revision it was drafted
    # from, so that revision is bound by the authorization as well.
    if review.get("lexiconSha256"):
        lexicon = root.parents[1] / "lexicon" / "lexicon.json"
        if lexicon.is_file():
            paths["lexiconSha256"] = lexicon
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
