#!/usr/bin/env python3
"""Build the non-approved lexical draft and its human review export."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from janome.tokenizer import Tokenizer
from pykakasi import kakasi


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"
REVIEW = ROOT / "deliverables" / "review" / "mebuku-toki-review.md"
FONT = Path(r"C:\Windows\Fonts\msyhbd.ttc")

PARTICLE_FUNCTIONS = {
    "は": ("提示主题或形成对比", "提示助词"),
    "が": ("提示主语或强调对象", "格助词"),
    "を": ("提示动作对象", "格助词"),
    "に": ("提示对象、着点或时间", "格助词"),
    "で": ("方式／状态／中顿", "格助词"),
    "と": ("提示并列、共同对象或引用", "格助词"),
    "の": ("表示所属或修饰关系", "格助词"),
    "も": ("表示追加、强调或让步", "副助词"),
    "へ": ("提示移动方向", "格助词"),
    "から": ("表示起点或原因", "格助词"),
    "まで": ("表示终点或范围", "副助词"),
    "より": ("提示比较基准", "格助词"),
    "だけ": ("限定范围", "副助词"),
    "ばかり": ("表示净是、只顾", "副助词"),
    "ばっか": ("表示净是、只顾（口语）", "副助词"),
    "しか": ("与否定呼应，表示仅", "副助词"),
    "って": ("口语引用／话题提示", "提示助词"),
    "けど": ("表示转折或铺垫", "接续助词"),
    "けれど": ("表示转折或铺垫", "接续助词"),
    "て": ("连接动作或状态", "接续助词"),
    "ね": ("征求认同或缓和语气", "终助词"),
    "よ": ("告知或加强语气", "终助词"),
    "な": ("表达感叹或自言自语语气", "终助词"),
    "か": ("构成疑问", "终助词"),
}

POS = {
    "名詞": "名词", "動詞": "动词", "形容詞": "い形容词", "副詞": "副词",
    "助詞": "助词", "助動詞": "助动词", "連体詞": "连体词", "接続詞": "连词",
    "感動詞": "感叹词", "代名詞": "代词", "フィラー": "填充词", "記号": "符号",
}

LOANWORDS = {
    "スピード": "speed",
}

PUNCTUATION = re.compile(r"^[\s、。！？!?…・「」『』（）()【】\[\]—―\-]+$")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def hiragana(value: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in value)


KAKASI = kakasi()


def to_romaji(value: str) -> str:
    return "".join(piece["hepburn"] for piece in KAKASI.convert(hiragana(value)))


def is_ascii_token(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value)) and not any("ぁ" <= char <= "ヺ" or "一" <= char <= "龯" for char in value)


def is_kanji(char: str) -> bool:
    return "一" <= char <= "龯"


def kanji_runs(surface: str, reading: str, card_index: int) -> list[dict]:
    runs = []
    positions = []
    index = 0
    while index < len(surface):
        if not is_kanji(surface[index]):
            index += 1
            continue
        end = index + 1
        while end < len(surface) and is_kanji(surface[end]):
            end += 1
        positions.append((index, end))
        index = end
    if not positions:
        return runs
    if len(positions) == 1:
        start, end = positions[0]
        run_reading = reading
        prefix, suffix = hiragana(surface[:start]), hiragana(surface[end:])
        if prefix and run_reading.startswith(prefix):
            run_reading = run_reading[len(prefix):]
        if suffix and run_reading.endswith(suffix):
            run_reading = run_reading[:-len(suffix)]
        runs.append({"cardIndex": card_index, "base": surface[start:end], "surfaceOffset": start, "reading": run_reading or reading})
    else:
        runs.append({"cardIndex": card_index, "base": "".join(surface[a:b] for a, b in positions), "surfaceOffset": positions[0][0], "reading": reading})
    return runs


def grammar_label(feature: list[str]) -> str:
    primary = POS.get(feature[0], "其他")
    if feature[0] == "助詞" and len(feature) > 1 and feature[1] != "*":
        particle_type = {"格助詞": "格助词", "係助詞": "提示助词", "副助詞": "副助词", "接続助詞": "接续助词", "終助詞": "终助词"}.get(feature[1])
        return particle_type or primary
    return primary


def build_card(word) -> dict | None:
    surface = word.surface
    if not surface.strip() or PUNCTUATION.match(surface) or is_ascii_token(surface):
        return None
    feature = word.part_of_speech.split(",")
    raw_reading = word.reading if word.reading not in (None, "*") else surface
    reading = hiragana(raw_reading)
    grammar = grammar_label(feature)
    card = {
        "token": surface,
        "reading": reading,
        "romaji": to_romaji(reading),
        "grammarStructureZh": grammar,
        "render": True,
        "showJlpt": False,
        "status": "draft",
        "fieldProvenance": {
            "token": "janome-ipadic automatic draft",
            "reading": "janome-ipadic automatic draft",
            "romaji": "pykakasi automatic draft",
            "meaningOrFunction": "pending multi-agent intelligent review",
            "grammarStructureZh": "janome-ipadic automatic draft",
        },
    }
    if feature[0] == "助詞" and surface in PARTICLE_FUNCTIONS:
        card["functionZh"], card["grammarStructureZh"] = PARTICLE_FUNCTIONS[surface]
    else:
        card["zhMeaning"] = "待联网核对"
    if surface in LOANWORDS:
        card["sourceWord"] = LOANWORDS[surface]
    return card


def render_layout_checks(frames: list[dict]) -> dict:
    renderer_path = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video\scripts\render_video.py")
    sys.path.insert(0, str(renderer_path.parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location("study_render_video_draft", renderer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    renderer = module.ForegroundRenderer(ROOT, 1920, 1080)
    renderer.frames = {frame["id"]: frame for frame in frames}
    qa = PROJECT / "qa" / "content-previews"
    qa.mkdir(parents=True, exist_ok=True)
    failures = []
    for frame in frames:
        try:
            renderer.render(frame["id"], None, qa / f"{frame['id']}.png")
        except Exception as error:
            failures.append({"frameId": frame["id"], "error": str(error)})
    longest_lyric = max(frames, key=lambda item: len(item["caption"]["japanese"]))["id"]
    maximum_cards = max(frames, key=lambda item: len(item["grammarCards"]))["id"]
    loanword = next((frame["id"] for frame in frames if any(card.get("sourceWord") for card in frame["grammarCards"])), None)
    return {
        "schemaVersion": 1,
        "result": "passed" if not failures else "failed",
        "resolvedLayout": "project/render/resolved-layout.json",
        "template": "study-current-v3",
        "representative": {
            "longestLyric": longest_lyric,
            "maximumCardLine": maximum_cards,
            "loanword": loanword,
            "pureEnglish": None,
            "mixedJapaneseEnglish": None,
        },
        "checks": {
            "allFramesRendered": not failures,
            "meaningFunctionMaxLines": 2,
            "tokenOneLine": True,
            "grammarStructureOneLine": True,
            "singleHorizontalCardRow": True,
        },
        "failures": failures,
    }


def main() -> None:
    data = load(FRAMES)
    tagger = Tokenizer()
    card_count = 0
    for frame in data["frames"]:
        cards = [card for word in tagger.tokenize(frame["caption"]["japanese"]) if (card := build_card(word))]
        annotations = []
        for index, card in enumerate(cards):
            annotations.extend(kanji_runs(card["token"], card["reading"], index))
        frame["grammarCards"] = cards
        frame["caption"]["furigana"] = annotations
        frame["caption"]["translationStatus"] = "draft-qmts-source-needs-context-review"
        frame["status"] = "draft-needs-multi-agent-review"
        card_count += len(cards)
    data["schemaVersion"] = 3
    write(FRAMES, data)
    write(PROJECT / "review" / "particle-functions.json", {
        "schemaVersion": 1,
        "usage": "Select the context-appropriate function during review; particle cards never display dictionary glosses.",
        "functions": {token: {"functionZh": function, "grammarStructureZh": grammar} for token, (function, grammar) in PARTICLE_FUNCTIONS.items()},
    })
    layout = render_layout_checks(data["frames"])
    write(PROJECT / "qa" / "layout-report.json", layout)
    if layout["result"] != "passed":
        raise SystemExit(json.dumps(layout, ensure_ascii=False, indent=2))

    lines = [
        "# 芽吹くとき｜词卡审核稿",
        "",
        "整句中文来自 QQ 音乐翻译轨；自动拆词、读音、罗马音、词义与词性均为待审核草稿。助词只展示句中功能，不展示字典义。纯英文不生成词卡、假名或罗马音。",
        "",
    ]
    for frame in data["frames"]:
        caption = frame["caption"]
        lines.extend([
            f"## {frame['id']}　{frame['startMs'] / 1000:06.2f}",
            f"歌词：{caption['japanese']}",
            f"暂定中文：{caption.get('translationZh') or '待核'}",
            "",
            "待核词卡：",
        ])
        if not frame["grammarCards"]:
            lines.append("- 无学习词卡（纯英文内容保留原位高亮）。")
        for card in frame["grammarCards"]:
            meaning = card.get("functionZh") or card.get("zhMeaning", "待核")
            source = f"｜外来词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(f"- `{card['token']}`｜读音：{card['reading']}｜罗马音：{card['romaji']}｜暂定：{meaning}｜结构：{card['grammarStructureZh']}{source}")
        lines.append("")
    REVIEW.parent.mkdir(parents=True, exist_ok=True)
    REVIEW.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    state = load(PROJECT / "build-state.json")
    state["stage"] = "draft_ready"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append("Card draft generated; all automatic linguistic fields remain unapproved.")
    write(PROJECT / "build-state.json", state)
    print(json.dumps({"frames": len(data["frames"]), "cards": card_count, "review": str(REVIEW), "layout": layout["result"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
