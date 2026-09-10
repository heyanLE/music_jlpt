import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\zattou-bokura-no-machi-v2")
frames_path = ROOT / "project" / "frames.json"
proposal_path = ROOT / "project" / "proposals" / "lexical.json"
out_path = ROOT / "project" / "proposals" / "lexical-v2.json"

raw = frames_path.read_bytes()
frames_doc = json.loads(raw)
proposal = copy.deepcopy(json.loads(proposal_path.read_text(encoding="utf-8")))
sha = hashlib.sha256(raw).hexdigest()
assert proposal["baseFrameSha256"] == sha, "v1 proposal is not based on current frames"

def compact(text: str) -> str:
    # QRC spacing and lyric punctuation never need separate learning cards.
    return re.sub(r"[\s\u3000、。！？?!…・「」『』（）()\[\]【】]", "", text)

by_key = {(x["frameId"], x["field"]): x for x in proposal["changes"]}

# In the opening line, make 「この夜」 a single semantic learning chunk, so it is
# explicitly reviewable alongside 鼓動 while still preserving exact token coverage.
l006 = by_key[("l006", "grammarCards")]["new"]
for i, card in enumerate(l006):
    if card["token"] == "この":
        assert l006[i + 1]["token"] == "夜"
        l006[i:i + 2] = [{
            "token": "この夜", "reading": "このよる", "romaji": "kono yoru",
            "zhMeaning": "这个夜晚", "posZh": "连体词＋名词", "grammarStructureZh": "连体词＋名词",
            "render": True, "showJlpt": False, "reviewRequired": True,
        }]
        break
else:
    raise AssertionError("l006 lacks this-night segment")

# Keep the possession particle visible instead of burying it inside a noun gloss.
l009 = by_key[("l009", "grammarCards")]["new"]
for i, card in enumerate(l009):
    if card["token"] == "自分自身":
        assert l009[i + 1]["token"] == "もの"
        l009.insert(i + 1, {
            "token": "の", "reading": "の", "romaji": "no", "functionZh": "表示所属、修饰",
            "posZh": "助词", "grammarStructureZh": "助词",
            "render": True, "showJlpt": False, "reviewRequired": True,
        })
        break
else:
    raise AssertionError("l009 lacks possessive segment")

def particle(frame_id, after_token, token, function):
    cards = by_key[(frame_id, "grammarCards")]["new"]
    for i, card in enumerate(cards):
        if card["token"] == after_token:
            cards.insert(i + 1, {
                "token": token, "reading": token, "romaji": {"を": "o", "の": "no"}[token],
                "functionZh": function, "posZh": "助词", "grammarStructureZh": "助词",
                "render": True, "showJlpt": False, "reviewRequired": True,
            })
            return
    raise AssertionError(f"{frame_id}: cannot insert {token} after {after_token}")

# The original draft collapsed these short but important particles/repetitions.
for fid in ("l013",): particle(fid, "声", "を", "提示动作对象")
for fid in ("l015", "l044", "l047"): particle(fid, {"l015": "街", "l044": "いつも通り", "l047": "灰色"}[fid], "の", "表示所属、修饰")
for fid in ("l035", "l063"): particle(fid, "自分自身", "の", "表示所属、修饰")

for fid in ("l025", "l053"):
    cards = by_key[(fid, "grammarCards")]["new"]
    cards.append({"token":"ほら","reading":"ほら","romaji":"hora","functionZh":"提醒对方看、听或注意","posZh":"感叹词","grammarStructureZh":"感叹词","render":True,"showJlpt":False,"reviewRequired":True})
for fid in ("l031", "l059"):
    cards = by_key[(fid, "grammarCards")]["new"]
    cards.extend([
        {"token":"まだ","reading":"まだ","romaji":"mada","zhMeaning":"还；仍然","posZh":"副词","grammarStructureZh":"副词","render":True,"showJlpt":False,"reviewRequired":True},
        {"token":"まだ","reading":"まだ","romaji":"mada","zhMeaning":"还；仍然","posZh":"副词","grammarStructureZh":"副词","render":True,"showJlpt":False,"reviewRequired":True},
    ])

cards = by_key[("l066", "grammarCards")]["new"]
for i, card in enumerate(cards):
    if card["token"] == "僕":
        cards.insert(i + 1, {"token":"次第","reading":"しだい","romaji":"shidai","zhMeaning":"取决于；视……而定","posZh":"名词","grammarStructureZh":"名词","render":True,"showJlpt":False,"reviewRequired":True})
        break
else:
    raise AssertionError("l066 lacks 僕 segment")

coverage = []
for frame in frames_doc["frames"]:
    fid = frame["id"]
    target = compact(frame["caption"]["japanese"])
    furi = by_key.get((fid, "caption.furigana"))
    cards = by_key.get((fid, "grammarCards"))
    assert furi is not None and cards is not None, f"{fid}: missing required proposal fields"
    assert isinstance(furi["new"], list), f"{fid}: furigana must be an array"
    items = cards["new"]
    assert items, f"{fid}: empty grammarCards"
    tokens = "".join(item["token"] for item in items)
    actual = compact(tokens)
    assert actual == target, f"{fid}: token coverage mismatch: {actual!r} != {target!r}"
    for card in items:
        assert card.get("reading") and card.get("romaji"), f"{fid}: reading/romaji missing"
        assert bool(card.get("zhMeaning")) ^ bool(card.get("functionZh")), f"{fid}: meaning/function invalid"
        assert card.get("posZh") and card.get("grammarStructureZh"), f"{fid}: POS display missing"
        assert card["grammarStructureZh"] == card["posZh"], f"{fid}: display line must be short POS"
    coverage.append({
        "frameId": fid,
        "caption": frame["caption"]["japanese"],
        "tokenConcat": tokens,
        "normalizedCaption": target,
        "normalizedTokenConcat": actual,
        "passed": True,
        "cardCount": len(items),
        "furiganaCount": len(furi["new"]),
    })

assert len(coverage) == 61
assert all(row["passed"] for row in coverage)
proposal["schemaVersion"] = 4
proposal["baseFrameSha256"] = sha
proposal["reviewRole"] = "lexical-full-coverage"
proposal["coverageAssertions"] = coverage
proposal["reviewNotes"] = {
    "coverage": "61/61 lyric frames passed character-exact token concatenation after ignoring QRC spaces and lyric punctuation.",
    "l006": "Explicitly includes 鼓動 and semantic chunk この夜.",
    "loanwordPolicy": "No true katakana loanword tokens occur in these 61 Japanese lyric frames; no sourceWord entries are proposed.",
    "cardDisplay": "Exactly one zhMeaning/functionZh per card; grammarStructureZh is the short third-line POS display.",
}
out_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "passed", "baseFrameSha256": sha, "frameCount": len(coverage), "cardCount": sum(x["cardCount"] for x in coverage), "out": str(out_path)}, ensure_ascii=False))
