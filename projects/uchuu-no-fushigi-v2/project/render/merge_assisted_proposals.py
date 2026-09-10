from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"C:\project\musicjlpt\projects\uchuu-no-fushigi-v2")
FRAMES_PATH = ROOT / "project" / "frames.json"
STATE_PATH = ROOT / "project" / "build-state.json"
MERGE_LOG_PATH = ROOT / "project" / "review" / "merge-log.json"
REVIEW_PATH = ROOT / "deliverables" / "review" / "uchuu-no-fushigi-v2-review.md"
MERGE_ID = "assisted-review-20260817-user-approved-all"
STATUS = "assisted-merged-awaiting-human-confirmation"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def card(token, reading, romaji, pos, *, meaning=None, function=None):
    result = {
        "token": token,
        "reading": reading,
        "romaji": romaji,
        "posZh": pos,
        "status": STATUS,
        "fieldProvenance": MERGE_ID,
    }
    if meaning is not None:
        result["zhMeaning"] = meaning
    if function is not None:
        result["functionZh"] = function
    return result


def find_card(frame, token, occurrence=1):
    seen = 0
    for value in frame["grammarCards"]:
        if value["token"] == token:
            seen += 1
            if seen == occurrence:
                return value
    raise KeyError(f"{frame['id']}: card {token!r} occurrence {occurrence}")


def set_card(frame, token, occurrence=1, **updates):
    value = find_card(frame, token, occurrence)
    value.update(updates)
    if "functionZh" in updates:
        value.pop("zhMeaning", None)
    if "zhMeaning" in updates:
        value.pop("functionZh", None)
    value["status"] = STATUS
    value["fieldProvenance"] = MERGE_ID


def mark_frame(frame, fields):
    frame["status"] = STATUS
    provenance = frame.setdefault("fieldProvenance", {})
    for field in fields:
        provenance[field] = MERGE_ID


def add_furigana(frame, items):
    existing = frame["caption"].setdefault("furigana", [])
    for item in items:
        if item not in existing:
            existing.append(item)


def main():
    payload = read_json(FRAMES_PATH)
    frames = {frame["id"]: frame for frame in payload["frames"]}
    changed = []

    # l001–l009: terminal particles/functions and scoped lexical refinements.
    for frame_id in ("l001", "l002", "l003", "l006", "l007"):
        frame = frames[frame_id]
        set_card(frame, "の", posZh="终助词", functionZh="疑问、寻求说明")
        mark_frame(frame, ["grammarCards"])
        changed.append(frame_id)
    set_card(frames["l002"], "ねてる", posZh="动词（ている缩约）", zhMeaning="正在睡（寝ている）")
    set_card(frames["l007"], "寂しく", posZh="形容词", zhMeaning="寂寞地")
    set_card(frames["l007"], "なる", posZh="动词", zhMeaning="变得、成为")
    set_card(frames["l008"], "はんぶんこ", posZh="名词", zhMeaning="平分；一人一半")
    set_card(frames["l009"], "のに", posZh="终助词", functionZh="表达未实现的愿望或遗憾（要是……就好了）")
    set_card(frames["l009"], "ね", posZh="终助词", functionZh="征求共鸣、语气柔和")
    mark_frame(frames["l008"], ["grammarCards"])
    mark_frame(frames["l009"], ["grammarCards"])
    changed.extend(["l008", "l009"])

    # Exact repeated surface text still has three separately timed QRC words.
    for frame_id in ("l004", "l025", "l027"):
        frame = frames[frame_id]
        frame["caption"]["romaji"] = "zenbu zenbu zenbu"
        mark_frame(frame, ["caption"])
        changed.append(frame_id)

    # l005/l026/l028 are independently edited (no automatic repeat inheritance).
    for frame_id in ("l005", "l026", "l028"):
        frame = frames[frame_id]
        set_card(frame, "さがし", posZh="动词（连用形）", zhMeaning="寻找（探す的连用形）")
        set_card(frame, "に", posZh="格助词", functionZh="表示移动动作的目的")
        set_card(frame, "ゆこう", posZh="动词（意志形）", zhMeaning="去吧、一起去吧（行く〔ゆく〕的意志形）")
        mark_frame(frame, ["grammarCards"])
        changed.append(frame_id)

    # l010: supply kanji-only ruby and make the learning units explicit.
    frame = frames["l010"]
    frame["caption"]["romaji"] = "warattari nayande mitari"
    add_furigana(frame, [{"base": "笑", "reading": "わら"}, {"base": "悩", "reading": "なや"}])
    first = find_card(frame, "笑ったり")
    first.update({"zhMeaning": "时而笑笑", "posZh": "动词＋列举助词", "status": STATUS, "fieldProvenance": MERGE_ID})
    second_index = next(i for i, c in enumerate(frame["grammarCards"]) if c["token"] == "悩んでみたり")
    frame["grammarCards"][second_index:second_index + 1] = [
        card("悩んで", "なやんで", "nayande", "动词（て形）", meaning="烦恼着"),
        card("みたり", "みたり", "mitari", "补助动词＋列举助词", meaning="试着……等"),
    ]
    mark_frame(frame, ["caption", "furigana", "grammarCards"])
    changed.append("l010")

    # l012–l014: coherent cross-line translation and lexical aspect.
    frame = frames["l012"]
    frame["caption"]["translationZh"] = "我们来解开宇宙的奥秘……"
    set_card(frame, "で", posZh="格助词", functionZh="共同动作的主体（由我们一起）")
    mark_frame(frame, ["caption", "grammarCards"])
    changed.append("l012")
    frame = frames["l013"]
    frame["caption"]["translationZh"] = "……试着解开看看吧。"
    mark_frame(frame, ["caption"])
    changed.append("l013")
    frame = frames["l014"]
    set_card(frame, "輝いてる", posZh="动词（ている缩约）", zhMeaning="正闪耀着")
    mark_frame(frame, ["grammarCards"])
    changed.append("l014")

    # l017: two terminal particles, each with a separate teaching function.
    frame = frames["l017"]
    set_card(frame, "なんて", posZh="副助词", functionZh="举例并弱化／轻视前项（≈など）")
    index = next(i for i, c in enumerate(frame["grammarCards"]) if c["token"] == "のかな")
    frame["grammarCards"][index:index + 1] = [
        card("の", "の", "no", "终助词", function="补充说明并引出疑问"),
        card("かな", "かな", "kana", "终助词", function="自问、推测"),
    ]
    mark_frame(frame, ["grammarCards"])
    changed.append("l017")

    # l018/l019: preserve frozen QRC display surface and only repair annotations/cards.
    frame = frames["l018"]
    add_furigana(frame, [{"base": "小", "reading": "ちい"}, {"base": "歌", "reading": "うた"}])
    mark_frame(frame, ["furigana"])
    changed.append("l018")
    frame = frames["l019"]
    frame["caption"]["translationZh"] = "你一定会忘掉，不过……"
    set_card(frame, "忘れちゃう", posZh="动词（てしまう的缩约）", zhMeaning="终究会忘掉")
    set_card(frame, "けど", posZh="接续助词", functionZh="但是、不过")
    mark_frame(frame, ["caption", "grammarCards"])
    changed.append("l019")

    # l020–l024: aspect, concessive construction, translation, and duplicate ruby.
    frame = frames["l020"]
    frame["caption"]["translationZh"] = "我会一直记得哦。"
    set_card(frame, "覚えている", posZh="动词（ている形）", zhMeaning="记得、一直记着")
    set_card(frame, "よ", posZh="终助词", functionZh="告知、强调语气")
    mark_frame(frame, ["caption", "grammarCards"])
    changed.append("l020")
    frame = frames["l021"]
    frame["caption"]["translationZh"] = "即使长大了也会记得哦。"
    index = next(i for i, c in enumerate(frame["grammarCards"]) if c["token"] == "なっても")
    frame["grammarCards"][index:index + 1] = [
        card("なって", "なって", "natte", "动词（て形）", meaning="变成了"),
        card("も", "も", "mo", "系助词", function="让步：即使……也……"),
    ]
    set_card(frame, "ね", posZh="终助词", functionZh="征求认同、柔和语气")
    mark_frame(frame, ["caption", "grammarCards"])
    changed.append("l021")
    frame = frames["l022"]
    frame["caption"]["translationZh"] = "今天要聊什么样的话题呢？"
    mark_frame(frame, ["caption"])
    changed.append("l022")
    frame = frames["l023"]
    frame["caption"]["translationZh"] = "要和你一起唱什么样的歌呢？"
    frame["caption"]["furigana"] = [
        {"base": "君", "reading": "きみ"},
        {"base": "歌", "reading": "うた", "occurrence": 1},
        {"base": "歌", "reading": "うた", "occurrence": 2},
    ]
    mark_frame(frame, ["caption", "furigana"])
    changed.append("l023")
    frame = frames["l024"]
    frame["caption"]["translationZh"] = "连谁都尚未知晓的花，也……"
    set_card(frame, "も", 1, posZh="系助词", functionZh="与否定搭配：任何……也不")
    set_card(frame, "も", 2, posZh="系助词", functionZh="添加、承接后句：也……")
    mark_frame(frame, ["caption", "grammarCards"])
    changed.append("l024")

    # Make all touched cards/provenance explicit, without claiming human confirmation.
    for frame_id in sorted(set(changed)):
        frame = frames[frame_id]
        for value in frame["grammarCards"]:
            if value.get("fieldProvenance") == MERGE_ID:
                value["status"] = STATUS
        frame["status"] = STATUS

    write_json(FRAMES_PATH, payload)
    frame_sha = hashlib.sha256(FRAMES_PATH.read_bytes()).hexdigest()
    merge_log = {
        "schemaVersion": 1,
        "mergeId": MERGE_ID,
        "userAuthorization": "采纳全部提案",
        "proposalFiles": [
            "project/proposals/early-l001-l010.json",
            "project/proposals/middle-l011-l019.json",
            "project/proposals/late-l020-l028.json",
        ],
        "changedFrameIds": sorted(set(changed)),
        "frozenSourceExceptions": [
            {
                "frameId": "l018",
                "decision": "Preserved QM/QRC Japanese surface text; only furigana annotations/cards were corrected.",
            }
        ],
        "frameSha256": frame_sha,
        "reviewDecision": "not-created; user authorized proposal merge, not final content approval/render",
    }
    write_json(MERGE_LOG_PATH, merge_log)

    lines = ["# うちゅうのふしぎ — 词卡人工审阅", "", "本文件已合并联网提案；所有变更仍标记为“已辅助合并，待人工最终确认”。", ""]
    for frame in payload["frames"]:
        c = frame["caption"]
        lines.extend([f"## {frame['id']}  {c['japanese']}", "", f"- 暂定中文：{c['translationZh']}", f"- 罗马音：{c['romaji']}", "- 词卡："])
        for item in frame["grammarCards"]:
            gloss = item.get("functionZh") or item.get("zhMeaning") or ""
            lines.append(f"  - {item['token']}｜{item['reading']}｜{item['romaji']}｜{gloss}｜{item['posZh']}")
        lines.append("")
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    state = read_json(STATE_PATH)
    state["state"] = "draft_ready"
    state["next"] = "review_approved"
    state.setdefault("activeFiles", {})["mergeLog"] = "project/review/merge-log.json"
    notes = [note for note in state.get("notes", []) if "No final render" not in note]
    notes.extend([
        "User authorized all assisted-review proposals; merged changes await final human content confirmation.",
        "No review-decision.json or render-authorization.json exists.",
        "No final render is authorized.",
    ])
    state["notes"] = notes
    write_json(STATE_PATH, state)


if __name__ == "__main__":
    main()
