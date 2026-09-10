import hashlib
import json
from pathlib import Path

root = Path(r"C:\project\musicjlpt\projects\uchuu-no-fushigi-v2")
frames = root / "project" / "frames.json"
decision = root / "project" / "review" / "review-decision.json"
value = json.loads(decision.read_text(encoding="utf-8"))
value["frameSha256"] = hashlib.sha256(frames.read_bytes()).hexdigest()
value["authorizationText"] = "把歌词里也改成词卡的样子，然后补充新增的假名填充"
value["displayNormalization"] = {"frameIds": ["l018", "l019", "l020", "l021"], "qrcTimingPreserved": True}
decision.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
json.loads(decision.read_text(encoding="utf-8"))
