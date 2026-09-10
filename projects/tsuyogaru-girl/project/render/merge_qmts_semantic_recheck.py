"""Merge the user-approved QMTS semantic recheck proposal without touching protected fields."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\project\musicjlpt\projects\tsuyogaru-girl")
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
MERGE_ID = "qmts-semantic-recheck-r01-user-approved"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def card(token, reading, romaji, meaning, pos, source_word=None, function=False):
    result = {"token": token, "reading": reading, "romaji": romaji, "posZh": pos,
              "status": "human-confirmed", "fieldProvenance": MERGE_ID}
    result["functionZh" if function else "zhMeaning"] = meaning
    if source_word:
        result["sourceWord"] = source_word
    return result


def main():
    data = load(FRAMES)
    by_id = {frame["id"]: frame for frame in data["frames"]}
    changed = []

    def replace(frame_id, cards):
        by_id[frame_id]["grammarCards"] = cards
        by_id[frame_id]["status"] = "human-confirmed"
        by_id[frame_id].setdefault("fieldProvenance", {})["grammarCards"] = MERGE_ID
        changed.append(frame_id)

    f = by_id["l007"]
    f["grammarCards"][0]["zhMeaning"] = "天生自带的、与生俱来的"
    f["grammarCards"][0]["posZh"] = "名词性短语"
    f["grammarCards"][0]["fieldProvenance"] = MERGE_ID
    changed.append("l007")

    f = by_id["l008"]
    f["grammarCards"][-1]["zhMeaning"] = "失败群像剧；失败者们的群像剧"
    f["grammarCards"][-1]["fieldProvenance"] = MERGE_ID
    f["status"] = "human-confirmed"; f.setdefault("fieldProvenance", {})["grammarCards"] = MERGE_ID
    changed.append("l008")

    replace("l009", [
        card("ドキドキして", "ドキドキして", "dokidoki shite", "心跳怦怦、忐忑不安着", "副词／拟声词＋する（て形）"),
        card("ズキズキする", "ズキズキする", "zukizuki suru", "一阵阵隐隐作痛", "副词／拟声词＋する")])
    replace("l016", [
        card("謎に", "なぞに", "nazo ni", "莫名地、不可思议地", "副词性短语"),
        card("走りたく", "はしりたく", "hashiritaku", "想跑（走りたい的连用形）", "动词＋希望助动词"),
        card("なって", "なって", "natte", "变得、成为", "动词（なる的て形）")])
    replace("l019", [
        card("ピースして", "ピースして", "piisu shite", "保持和平、保持平和状态", "外来语名词＋する（て形）", "peace")])

    f = by_id["l020"]
    replace("l020", f["grammarCards"][:4] + [
        card("負けてやれ", "まけてやれ", "makete yare", "尽管失败吧、索性输个痛快吧", "动词（て形＋やる命令形）")])
    f = by_id["l021"]
    replace("l021", f["grammarCards"][:2] + [
        card("強くなる", "つよくなる", "tsuyoku naru", "变得坚强", "形容词く形＋动词")])
    f = by_id["l038"]
    replace("l038", f["grammarCards"][:2] + [
        card("命中3%", "めいちゅうさんパーセント", "meichuu san paasento", "命中率只有3%", "名词＋数量表达")])

    f = by_id["l043"]
    f["grammarCards"][2]["zhMeaning"] = "续关、继续挑战"
    f["grammarCards"][2]["fieldProvenance"] = MERGE_ID
    f["status"] = "human-confirmed"; f.setdefault("fieldProvenance", {})["grammarCards"] = MERGE_ID
    changed.append("l043")

    f = by_id["l047"]
    replace("l047", f["grammarCards"][:2] + [
        card("胸に秘め", "むねにひめ", "mune ni hime", "深藏于心中", "名词＋格助词＋动词连用形")])
    f = by_id["l051"]
    replace("l051", [
        card("ずっと", "ずっと", "zutto", "一直", "副词"),
        card("信じ続け", "しんじつづけ", "shinji tsuzuke", "持续相信、始终坚信", "动词＋补助动词（连用形）"),
        card("ながら", "ながら", "nagara", "表示同时进行", "接续助词", function=True)])
    f = by_id["l052"]
    replace("l052", [
        card("いつか", "いつか", "itsuka", "总有一天", "副词"),
        card("大人になる", "おとなになる", "otona ni naru", "长大成人", "名词＋格助词＋动词"),
        card("けど", "けど", "kedo", "表示转折、铺垫后文", "接续助词", function=True)])

    f = by_id["l054"]
    f["grammarCards"][2]["zhMeaning"] = "彻底品味、全盘接受吧"
    f["grammarCards"][2]["fieldProvenance"] = MERGE_ID
    f["status"] = "human-confirmed"; f.setdefault("fieldProvenance", {})["grammarCards"] = MERGE_ID
    changed.append("l054")

    f = by_id["l059"]
    replace("l059", [
        card("ヒロインになる", "ヒロインになる", "hiroin ni naru", "成为女主角", "外来语名词＋格助词＋动词", "heroine"),
        card("と", "と", "to", "引用誓言的内容", "格助词", function=True),
        card("胸", "むね", "mune", "心中", "名词"),
        card("に", "に", "ni", "表示动作归着处", "格助词", function=True),
        card("誓い", "ちかい", "chikai", "起誓", "动词（连用形）"),
        card("ながら", "ながら", "nagara", "表示同时进行", "接续助词", function=True)])

    write(FRAMES, data)
    frame_sha = hashlib.sha256(FRAMES.read_bytes()).hexdigest()
    write(PROJECT / "review" / "merge-log.json", {
        "schemaVersion": 1, "mergeId": MERGE_ID, "userAuthorization": "采纳全部提案",
        "proposal": "project/proposals/qmts-semantic-recheck-r01.json", "changedFrameIds": changed,
        "preservedUserCorrections": ["l001:負け", "l068:負け", "l069:負け"], "frameSha256": frame_sha})
    write(PROJECT / "review" / "review-decision.json", {
        "content": "approved", "scope": "qmts-semantic-recheck-r01", "renderAuthorized": False,
        "frameSha256": frame_sha, "authorizationText": "采纳全部提案"})
    lines = ["# つよがるガール — 整句中文校准后词卡审阅", ""]
    for frame in data["frames"]:
        caption = frame["caption"]
        lines += [f"## {frame['id']}  {caption['japanese']}", "", f"- 整句中文：{caption['translationZh']}", "- 词卡："]
        for value in frame["grammarCards"]:
            lines.append(f"  - {value['token']}｜{value['reading']}｜{value['romaji']}｜{value.get('functionZh') or value.get('zhMeaning', '')}｜{value['posZh']}")
        lines.append("")
    review_path = ROOT / "deliverables" / "review" / "tsuyogaru-girl-review.md"
    review_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    state = load(PROJECT / "build-state.json")
    state.update({"state": "review_approved", "next": "await_render_authorization", "runId": "20260818-qmts-semantic-r01"})
    state.setdefault("activeFiles", {}).update({"frames": "project/frames.json", "review": "deliverables/review/tsuyogaru-girl-review.md", "mergeLog": "project/review/merge-log.json", "reviewDecision": "project/review/review-decision.json"})
    state["notes"] = ["QMTS semantic recheck proposal accepted by user.", "All protected user corrections were preserved.", "No final render is authorized."]
    write(PROJECT / "build-state.json", state)


if __name__ == "__main__":
    main()
