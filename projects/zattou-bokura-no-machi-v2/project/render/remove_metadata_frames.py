from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def main() -> None:
    path = PROJECT / "frames.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    before = data["frames"]
    removed_ids = {"l001", "l002", "l003", "l004", "l005"}
    kept = [frame for frame in before if frame["id"] not in removed_ids]
    if len(kept) != len(before) - len(removed_ids):
        raise SystemExit("Expected QRC metadata frames l001-l005 were not all present")
    data["frames"] = kept
    data["metadataPolicy"] = "QRC title/artist/album/credits rows excluded from display"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    for proposal in (PROJECT / "proposals").glob("*.json"):
        proposal.rename(proposal.with_suffix(proposal.suffix + ".stale-after-metadata-filter"))
    audit = PROJECT / "review" / "assisted-review-audit.json"
    if audit.exists():
        audit.rename(audit.with_suffix(audit.suffix + ".stale-after-metadata-filter"))
    print(json.dumps({"removed": sorted(removed_ids), "remainingFrames": len(kept)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
