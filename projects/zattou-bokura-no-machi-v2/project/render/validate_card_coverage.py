from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"

IGNORED = re.compile(r"[\s\u3000\(\)（）『』「」【】、。！？!?,.・…—\-]+")


def compact(value: str) -> str:
    return IGNORED.sub("", value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposal", type=Path)
    args = parser.parse_args()
    frames = {frame["id"]: frame for frame in json.loads((PROJECT / "frames.json").read_text(encoding="utf-8"))["frames"]}
    proposal = json.loads(args.proposal.read_text(encoding="utf-8"))
    if isinstance(proposal.get("frames"), list):
        # Integrated-review documents carry complete proposed frames rather than
        # field-level changes.
        cards = {frame["id"]: frame.get("grammarCards", []) for frame in proposal["frames"]}
    else:
        cards = {change["frameId"]: change["new"] for change in proposal.get("changes", []) if change.get("field") == "grammarCards"}
    missing, mismatch = [], []
    for frame_id, frame in frames.items():
        if frame_id not in cards:
            missing.append(frame_id)
            continue
        source = compact(frame["caption"]["japanese"])
        rebuilt = compact("".join(card.get("token", "") for card in cards[frame_id]))
        if source != rebuilt:
            mismatch.append({"frameId": frame_id, "source": source, "rebuilt": rebuilt})
    report = {"proposal": str(args.proposal), "frames": len(frames), "missing": missing, "mismatch": mismatch, "passed": not missing and not mismatch}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
