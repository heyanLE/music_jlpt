#!/usr/bin/env python3
"""Run deterministic palette, layout, and setup validation after lyrics are normalized."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve(); project = root / "project"; skill = Path(__file__).resolve().parents[1]
    manifest = load(project / "input-manifest.json")
    subprocess.run([sys.executable, str(skill / "scripts" / "derive_palette.py"), str(root / manifest["cover"]["asset"]), str(project / "palette.json")], check=True)
    for index, output in enumerate(manifest["outputs"]):
        suffix = "" if len(manifest["outputs"]) == 1 else f"-{output['name']}"
        resolved = project / "render" / f"resolved-layout{suffix}.json"
        subprocess.run([
            sys.executable, str(skill / "scripts" / "resolve_layout.py"), str(project / "templates" / "foreground.json"), str(project / "palette.json"),
            str(resolved), "--width", str(output["width"]), "--height", str(output["height"]),
        ], check=True)
        if index == 0 and resolved.name != "resolved-layout.json":
            shutil.copyfile(resolved, project / "render" / "resolved-layout.json")
    subprocess.run([sys.executable, str(skill / "scripts" / "validate_project.py"), str(root), "--stage", "setup"], check=True)
    print(json.dumps({"project": str(root), "outputs": [item["name"] for item in manifest["outputs"]], "result": "passed"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
