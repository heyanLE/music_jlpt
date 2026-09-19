#!/usr/bin/env python3
"""Bootstrap or repair the runtime this skill needs, then report where everything is.

`check_runtime.py` is the read-only inventory: it never changes the machine. This script is
its mutating counterpart - it installs the pinned Python dependencies, tells you exactly what
is missing and how to fix it, and can install the pinned QRC decoder runtime on request.

Run it after cloning on a new machine/context:

    python -B SKILL_ROOT/scripts/bootstrap_env.py            # check, install what is missing
    python -B SKILL_ROOT/scripts/bootstrap_env.py --check     # report only, change nothing
    python -B SKILL_ROOT/scripts/bootstrap_env.py --install-decoder   # QRC decoding needs Node

Exit codes: 0 = ready, 1 = something required is still missing (the report says what).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = SKILL_ROOT / "requirements.txt"
MIN_PYTHON = (3, 10)
# The series font. Not redistributed (proprietary); a clone must supply its own via STUDY_FONT.
DEFAULT_FONTS = [
    Path("C:/Windows/Fonts/msyhbd.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]


def report() -> dict:
    found: dict = {"python": sys.version, "pythonPath": sys.executable, "platform": sys.platform}
    found["pythonOk"] = sys.version_info[:2] >= MIN_PYTHON
    try:
        import PIL
        found["Pillow"] = PIL.__version__
    except ImportError:
        found["Pillow"] = None
    try:
        import numpy
        found["numpy"] = numpy.__version__
    except ImportError:
        found["numpy"] = None
    for tool in ("ffmpeg", "ffprobe", "node", "npm"):
        found[tool] = shutil.which(tool)
    explicit = os.environ.get("STUDY_FONT")
    font = Path(explicit) if explicit else next((path for path in DEFAULT_FONTS if path.is_file()), None)
    found["font"] = str(font) if font else None
    found["fontSource"] = "STUDY_FONT" if explicit else ("default" if font else None)
    found["qrcRuntime"] = any((SKILL_ROOT.parent.parent.parent / "projects").glob(
        "*/project/work/qrc-runtime/node_modules/smart-lyric/package.json"))
    return found


def install_python_dependencies() -> str:
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
               "--requirement", str(REQUIREMENTS)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return "installed" if result.returncode == 0 else f"failed: {(result.stderr or result.stdout).strip()[-300:]}"


def install_qrc_decoder() -> str:
    """Install the pinned decoder into the skill so every project can reuse it."""
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        return "skipped: npm is not on PATH (only needed to decode encrypted QRC files)"
    runtime = SKILL_ROOT / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    command = [npm, "install", "--prefix", str(runtime), "--no-audit", "--no-fund", "smart-lyric@1.0.4"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return f"installed into {runtime}" if result.returncode == 0 else f"failed: {(result.stderr or result.stdout).strip()[-300:]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Report only; install nothing")
    parser.add_argument("--install-decoder", action="store_true", help="Install the pinned QRC decoder runtime")
    parser.add_argument("--out", type=Path, help="Also write the report here (keep it out of version control)")
    args = parser.parse_args()

    before = report()
    actions = {}
    if not args.check:
        if before["Pillow"] is None or before["numpy"] is None:
            actions["pythonDependencies"] = install_python_dependencies()
        if args.install_decoder:
            actions["qrcDecoder"] = install_qrc_decoder()
    found = report()

    problems = []
    if not found["pythonOk"]:
        problems.append(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required, found {found['python'].split()[0]}")
    for package in ("Pillow", "numpy"):
        if found[package] is None:
            problems.append(f"{package} is missing: install it with 'pip install -r {REQUIREMENTS.name}'")
    for tool in ("ffmpeg", "ffprobe"):
        if not found[tool]:
            problems.append(f"{tool} is not on PATH")
    if not found["font"]:
        problems.append("No bold CJK font found: set STUDY_FONT to a font you are licensed to use")
    if not found["node"] and not found["qrcRuntime"]:
        problems.append("node/npm not found and no installed QRC decoder: needed only to decode encrypted QRC files")

    document = {
        "schemaVersion": 1,
        "skillRoot": str(SKILL_ROOT),
        "requirements": str(REQUIREMENTS),
        "found": found,
        "actions": actions,
        "problems": problems,
        "ready": not problems,
        "note": "Optional tools (node/npm, the QRC decoder) matter only when importing encrypted QRC lyrics.",
    }
    print(json.dumps(document, ensure_ascii=False, indent=2))
    if args.out:
        args.out.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    raise SystemExit(0 if not problems else 1)


if __name__ == "__main__":
    main()
