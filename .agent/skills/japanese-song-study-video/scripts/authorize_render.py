#!/usr/bin/env python3
"""Record explicit user render authorization against the complete active hash set."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from verify_render_gate import authorization_hash_paths, sha, verify_review_gate


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--authorization-text", required=True, help="Verbatim user wording, e.g. 确认渲染")
    parser.add_argument("--renderer", type=Path, help="Fixed or custom renderer; defaults to render_video.py")
    args = parser.parse_args()
    root = args.project_root.resolve(); project = root / "project"; source = root / "source"
    wording = args.authorization_text.strip()
    if wording in {"继续", "开始", "可以", "下一步"}:
        raise SystemExit("Ambiguous wording is not render authorization; require explicit wording such as 确认渲染")
    review = verify_review_gate(root)
    renderer = (args.renderer.resolve() if args.renderer else Path(__file__).with_name("render_video.py").resolve())
    if not renderer.is_file():
        raise SystemExit(f"Renderer is missing: {renderer}")
    contract = {
        "schemaVersion": 3, "authorization": f"user: {wording}",
        "authorizedAt": datetime.now(timezone.utc).isoformat(), "renderAuthorized": True,
        **{key: sha(path) for key, path in authorization_hash_paths(root, renderer, review).items()},
    }
    output = project / "render-authorization.json"
    output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(output.read_text(encoding="utf-8"))
    print(json.dumps({"authorization": contract["authorization"], "hashes": len(authorization_hash_paths(root, renderer, review)), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
