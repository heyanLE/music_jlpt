"""Add the two user-supplied spoken MV captions on the output clock."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "project" / "frames.json"


def card(token, reading, romaji, meaning, grammar):
    return {"token": token, "reading": reading, "romaji": romaji, "zhMeaning": meaning,
            "grammarStructureZh": grammar, "posZh": grammar, "status": "user-supplied"}


PRELUDE = [
    {
        "id": "mv-p001", "clock": "output", "startMs": 7300, "endMs": 10500,
        "displayUnits": [{"kind": "japanese", "text": "ちょっと、転ばないでよ", "qrcParts": []}],
        "caption": {"japanese": "ちょっと、転ばないでよ",
                    "furigana": [{"base": "転", "reading": "ころ", "start": 5, "end": 6}],
                    "romaji": "chotto, korobanai de yo", "translationZh": "喂，可别摔倒啊。"},
        "grammarCards": [card("ちょっと", "ちょっと", "chotto", "喂；等一下", "感叹词"),
                         card("転ばないでよ", "ころばないでよ", "korobanai de yo", "可别摔倒啊", "动词ないで＋终助词")],
    },
    {
        "id": "mv-p002", "clock": "output", "startMs": 15000, "endMs": 18000,
        "displayUnits": [{"kind": "japanese", "text": "やっとここまで来れたね。", "qrcParts": []}],
        "caption": {"japanese": "やっとここまで来れたね。",
                    "furigana": [{"base": "来", "reading": "こ", "start": 7, "end": 8}],
                    "romaji": "yatto koko made koreta ne", "translationZh": "终于走到这里了呢。"},
        "grammarCards": [card("やっと", "やっと", "yatto", "终于", "副词"),
                         card("ここまで", "ここまで", "koko made", "到这里为止", "地点＋まで"),
                         card("来れた", "これた", "koreta", "能来到；终于来到", "来る可能形过去式"),
                         card("ね", "ね", "ne", "表示确认、寻求共鸣", "终助词")],
    },
]


def main() -> None:
    payload = json.loads(FRAMES.read_text(encoding="utf-8"))
    payload["frames"] = [frame for frame in payload["frames"] if not frame["id"].startswith("mv-p")] + PRELUDE
    payload["frames"].sort(key=lambda frame: frame["startMs"] + (0 if frame.get("clock") == "output" else 19_584))
    for frame in PRELUDE:
        frame["status"] = "user-supplied"
        frame["fieldProvenance"] = {"all": "user-supplied MV spoken-caption instruction"}
    FRAMES.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"added": [frame["id"] for frame in PRELUDE]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
