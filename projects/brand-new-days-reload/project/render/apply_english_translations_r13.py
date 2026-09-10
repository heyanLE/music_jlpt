"""Add provisional Chinese translations to the restored pure-English lyric rows."""
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
FRAMES_PATH = PROJECT / "project" / "frames.json"
PROPOSAL_PATH = PROJECT / "project" / "proposals" / "english-translations-r13.json"

translations = {
    "en-38088": "（满眼所见）",
    "en-52438": "（越过我蒙蔽的双眼）",
    "en-124726": "（我们早已这样告诉过你）",
    "en-139138": "（你告诉我哪里不对）",
    "en-172139": "我会引领崭新的日子。",
    "en-240187": "（一切都取决于你）",
    "en-254505": "（所以仰望着你）",
    "en-316440": "我会引领崭新的日子。"
}

doc = json.loads(FRAMES_PATH.read_text(encoding="utf-8"))
changed = []
for frame in doc["frames"]:
    translation = translations.get(frame["id"])
    if translation is None:
        continue
    if frame["caption"].get("translationZh"):
        raise RuntimeError(f"refusing to overwrite existing translation: {frame['id']}")
    frame["caption"]["translationZh"] = translation
    frame["translationProvenance"] = "assisted provisional translation; no QQ Music QMTS translation was supplied for this row"
    changed.append({"id": frame["id"], "english": frame["caption"]["japanese"], "translationZh": translation})

PROPOSAL_PATH.write_text(json.dumps({
    "runId": "20260817-r13-english-translations",
    "status": "user-requested provisional translations applied",
    "changed": changed
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
FRAMES_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"changed": len(changed)}, ensure_ascii=False))
