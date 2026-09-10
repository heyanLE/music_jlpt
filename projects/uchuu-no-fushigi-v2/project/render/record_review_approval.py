from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\uchuu-no-fushigi-v2")
FRAMES = ROOT / "project" / "frames.json"
STATE = ROOT / "project" / "build-state.json"
DECISION = ROOT / "project" / "review" / "review-decision.json"


def write_json(path: Path, value):
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


frame_sha = hashlib.sha256(FRAMES.read_bytes()).hexdigest()
write_json(DECISION, {
    "content": "approved",
    "scope": "all",
    "renderAuthorized": False,
    "frameSha256": frame_sha,
    "authorizationText": "确认词卡",
})
state = json.loads(STATE.read_text(encoding="utf-8"))
state["state"] = "review_approved"
state["next"] = "await_render_authorization"
state.setdefault("activeFiles", {})["reviewDecision"] = "project/review/review-decision.json"
state["notes"] = [note for note in state.get("notes", []) if "No review-decision" not in note]
state["notes"].append("Content approved; rendering requires a separate explicit authorization.")
write_json(STATE, state)
