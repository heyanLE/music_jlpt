"""Insert QRC pure-English rows without changing existing reviewed frames."""
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
FRAMES_PATH = PROJECT / "project" / "frames.json"
QRC_PATH = PROJECT / "deliverables" / "brand-new-days-qm.parsed.json"
PROPOSAL_PATH = PROJECT / "project" / "proposals" / "pure-english-lines-r09.json"

def qrc_text(row):
    return "".join(part.get("content", "") for part in row.get("content", []))

def is_pure_english(text):
    return bool(text.strip()) and bool(re.fullmatch(r"[\x00-\x7F]+", text)) and bool(re.search(r"[A-Za-z]", text))

frames_doc = json.loads(FRAMES_PATH.read_text(encoding="utf-8"))
qrc_doc = json.loads(QRC_PATH.read_text(encoding="utf-8"))
existing_starts = {frame["startMs"] for frame in frames_doc["frames"]}
added = []
for row in qrc_doc["content"]:
    text = qrc_text(row).strip()
    if not is_pure_english(text) or row["start"] in existing_starts:
        continue
    added.append({
        "id": f"en-{row['start']}",
        "startMs": row["start"],
        "endMs": row["start"] + row["duration"],
        "caption": {
            "japanese": text,
            "furigana": [],
            "romaji": "",
            "translationZh": ""
        },
        "grammarCards": [],
        "analysisStatus": "human-confirmed-english-line",
        "provenance": "QQ Music QM pure-English row; user-approved structural repair"
    })

PROPOSAL_PATH.parent.mkdir(parents=True, exist_ok=True)
PROPOSAL_PATH.write_text(json.dumps({
    "runId": "20260817-r09-pure-english-fix",
    "action": "insert missing pure-English QRC rows",
    "addedFrames": added
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
frames_doc["frames"] = sorted(frames_doc["frames"] + added, key=lambda frame: frame["startMs"])
FRAMES_PATH.write_text(json.dumps(frames_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"added": len(added), "ids": [frame["id"] for frame in added]}, ensure_ascii=False))
