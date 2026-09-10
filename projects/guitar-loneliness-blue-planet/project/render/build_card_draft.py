from __future__ import annotations

import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
LOCAL_SITE = PROJECT / "work" / "python-site"
SKILL = Path(r"C:\Users\eke_l\.codex\skills\japanese-song-study-video")
sys.path.insert(0, str(LOCAL_SITE))

from pykakasi import kakasi  # noqa: E402
from sudachipy import dictionary, tokenizer  # noqa: E402


KANJI_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff々〆ヵヶ]+")
JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff々〆ヵヶ]")
LATIN_RE = re.compile(r"[A-Za-z]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")

PARTICLE_FUNCTIONS = {
    "は": ("提示主题或形成对比", "提示助词"),
    "が": ("标记主语或强调对象", "格助词"),
    "を": ("标记动作对象", "格助词"),
    "に": ("标记对象或时空点", "格助词"),
    "で": ("表示场所、手段或原因", "格助词"),
    "と": ("表示共同对象、并列或引用", "格助词"),
    "の": ("表示所属、修饰或名词化", "格助词"),
    "も": ("表示追加、强调或让步", "副助词"),
    "へ": ("表示移动方向", "格助词"),
    "から": ("表示起点或原因", "格助词"),
    "まで": ("表示终点或范围", "副助词"),
    "より": ("表示比较基准", "格助词"),
    "だけ": ("限定范围", "副助词"),
    "ほど": ("表示程度或比较基准", "副助词"),
    "って": ("口语引用或提示话题", "提示助词"),
    "て": ("连接动作或状态", "接续助词"),
    "でて": ("表示中顿并连接后项", "接续形式"),
    "ね": ("征求认同或缓和语气", "终助词"),
    "よ": ("告知或加强语气", "终助词"),
    "か": ("构成疑问或表示不确定", "终助词"),
}

POS_ZH = {
    "名詞": "名词", "代名詞": "代词", "動詞": "动词", "形容詞": "い形容词",
    "形状詞": "な形容词", "副詞": "副词", "連体詞": "连体词", "接続詞": "连词",
    "助詞": "助词", "助動詞": "助动词", "感動詞": "感叹词", "接頭辞": "前缀",
    "接尾辞": "后缀",
}

PARTICLE_PRONUNCIATION = {"は": "わ", "へ": "え", "を": "お"}
LOANWORDS = {"ギター": "guitar"}
KKS = kakasi()
TOKENIZER = dictionary.Dictionary().create()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def kata_to_hira(text: str) -> str:
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in text)


def to_romaji(reading: str, surface: str = "") -> str:
    spoken = PARTICLE_PRONUNCIATION.get(surface, reading)
    return re.sub(r"\s+", "", "".join(piece.get("hepburn", "") for piece in KKS.convert(spoken))).lower()


def raw_tokens(text: str) -> list[dict]:
    result = []
    for morpheme in TOKENIZER.tokenize(text, tokenizer.Tokenizer.SplitMode.C):
        surface = morpheme.surface()
        pos = list(morpheme.part_of_speech())
        if pos[0] in {"空白", "補助記号"} or not JP_RE.search(surface):
            continue
        if LATIN_RE.search(surface) and not JP_RE.search(surface):
            continue
        reading = kata_to_hira(morpheme.reading_form())
        if not reading or reading == "*":
            reading = kata_to_hira(surface)
        result.append({
            "surface": surface,
            "reading": reading,
            "pos0": pos[0],
            "pos": pos,
            "dictionaryForm": morpheme.dictionary_form(),
            "merged": False,
        })
    return result


def should_merge(previous: dict, current: dict) -> bool:
    surface, pos0 = current["surface"], current["pos0"]
    prev_surface, prev_pos = previous["surface"], previous["pos0"]
    if prev_surface == "で" and surface == "も":
        return True
    if pos0 == "助動詞" and prev_pos in {"動詞", "形容詞", "助動詞"}:
        return True
    if surface in {"て", "で"} and pos0 == "助詞" and prev_pos in {"動詞", "形容詞"}:
        return True
    if surface in {"いる", "いく", "くる"} and prev_surface.endswith(("て", "で")):
        return True
    if surface in {"ない", "た", "だ", "ます", "れる", "られる", "せる", "させる"} and prev_pos in {"動詞", "形容詞", "助動詞"}:
        return True
    if surface == "に" and prev_surface == "よう":
        return True
    if surface == "だ" and prev_surface == "ん":
        return True
    return False


def merge_tokens(tokens: list[dict]) -> list[dict]:
    merged = []
    for current in tokens:
        if merged and should_merge(merged[-1], current):
            previous = merged[-1]
            previous["surface"] += current["surface"]
            previous["reading"] += current["reading"]
            previous["merged"] = True
            previous.setdefault("mergedParts", []).append({"surface": current["surface"], "pos0": current["pos0"]})
        else:
            merged.append(copy.deepcopy(current))
    return merged


def card_from_token(token: dict) -> dict:
    surface, reading, pos0 = token["surface"], token["reading"], token["pos0"]
    grammar = POS_ZH.get(pos0, "词性待复核")
    if token.get("merged"):
        grammar += "（活用）"
    card = {
        "token": surface,
        "reading": reading,
        "romaji": to_romaji(reading, surface),
        "grammarStructureZh": grammar,
        "dictionaryForm": token.get("dictionaryForm", surface),
        "render": True,
        "showJlpt": False,
        "status": "auto-draft-needs-assisted-review",
        "reviewRequired": True,
        "fieldProvenance": {
            "segmentation": "SudachiPy 0.6.11 + sudachidict_core 20260723",
            "reading": "SudachiPy 0.6.11 + sudachidict_core 20260723",
            "romaji": "pykakasi 2.3.0",
            "meaningOrFunction": "phase-3 unresolved draft",
            "grammarStructureZh": "Sudachi POS draft",
        },
    }
    if surface == "でも":
        card["zhMeaning"] = "但是；不过"
        card["grammarStructureZh"] = "连词"
        card["fieldProvenance"]["meaningOrFunction"] = "deterministic fixed-expression draft"
    elif pos0 == "助詞":
        function, structure = PARTICLE_FUNCTIONS.get(surface, ("功能待联网复核", grammar))
        card["functionZh"] = function
        card["grammarStructureZh"] = structure
        card["fieldProvenance"]["meaningOrFunction"] = "project particle-function draft table"
    else:
        card["zhMeaning"] = "待联网复核"
    if surface in LOANWORDS:
        card["sourceWord"] = LOANWORDS[surface]
        card["fieldProvenance"]["sourceWord"] = "curated loanword draft table"
    return card


def furigana_for_card(card: dict, lyric: str, search_start: int) -> tuple[list[dict], int]:
    token = card["token"]
    token_pos = lyric.find(token, search_start)
    if token_pos < 0:
        token_pos = lyric.find(token)
    next_search = search_start if token_pos < 0 else token_pos + len(token)
    runs = list(KANJI_RE.finditer(token))
    if token_pos < 0 or not runs:
        return [], next_search
    pattern, previous = "", 0
    for run in runs:
        pattern += re.escape(kata_to_hira(token[previous:run.start()])) + "(.+?)"
        previous = run.end()
    pattern += re.escape(kata_to_hira(token[previous:]))
    match = re.fullmatch(pattern, card["reading"])
    if not match:
        return [], next_search
    return [{
        "cardIndex": card["cardIndex"],
        "base": run.group(0),
        "surfaceOffset": run.start(),
        "reading": match.group(index + 1),
        "tokenStart": token_pos,
        "baseStart": token_pos + run.start(),
    } for index, run in enumerate(runs)], next_search


def enrich(frame: dict, cache: dict[str, dict]) -> dict:
    result = copy.deepcopy(frame)
    caption = result.setdefault("caption", {})
    lyric = caption.get("japanese", "")
    if lyric in cache:
        learned = copy.deepcopy(cache[lyric])
    else:
        cards = [card_from_token(token) for token in merge_tokens(raw_tokens(lyric))]
        for index, card in enumerate(cards):
            card["cardIndex"] = index
        furigana, search_start = [], 0
        for card in cards:
            entries, search_start = furigana_for_card(card, lyric, search_start)
            furigana.extend(entries)
            card.pop("cardIndex", None)
        learned = {"cards": cards, "furigana": furigana, "romaji": " ".join(card["romaji"] for card in cards)}
        cache[lyric] = copy.deepcopy(learned)
    if caption.get("romaji") and not caption.get("sourceRomaji"):
        caption["sourceRomaji"] = caption["romaji"]
    caption["romaji"] = learned["romaji"]
    caption["furigana"] = learned["furigana"]
    caption["translationStatus"] = "draft-qmts-source-needs-context-review"
    result["grammarCards"] = learned["cards"]
    result["analysisStatus"] = "phase-3-auto-draft"
    result["status"] = "draft-needs-multi-agent-review"
    result["reviewRequired"] = True
    result.setdefault("fieldProvenance", {})["grammarCards"] = "deterministic draft; pending multi-agent intelligent review"
    return result


def meaning(card: dict) -> str:
    return card.get("functionZh") or card.get("zhMeaning") or ""


def render_preflight(frames: list[dict]) -> tuple[list[dict], dict[str, str]]:
    renderer_path = SKILL / "scripts" / "render_video.py"
    sys.path.insert(0, str(renderer_path.parent))
    spec = importlib.util.spec_from_file_location("study_render_video_draft", renderer_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    renderer = module.ForegroundRenderer(ROOT, 1920, 1080)
    output_dir = PROJECT / "qa" / "draft-layout" / "states"
    output_dir.mkdir(parents=True, exist_ok=True)
    failures, paths = [], {}
    for frame in frames:
        path = output_dir / f"{frame['id']}.png"
        try:
            renderer.render(frame["id"], active_index=None, output=path, cover_visible=True)
            paths[frame["id"]] = str(path)
        except Exception as error:
            failures.append({"frameId": frame["id"], "error": str(error)})
    return failures, paths


def select_samples(frames: list[dict]) -> dict[str, str | None]:
    return {
        "longestLyric": max(frames, key=lambda frame: len(frame["caption"]["japanese"]))["id"],
        "maximumCardCount": max(frames, key=lambda frame: len(frame.get("grammarCards", [])))["id"],
        "longestMeaningOrFunction": max(frames, key=lambda frame: max([len(meaning(card)) for card in frame.get("grammarCards", [])] or [0]))["id"],
        "mixedJapaneseEnglish": next((frame["id"] for frame in frames if LATIN_RE.search(frame["caption"]["japanese"]) and JP_RE.search(frame["caption"]["japanese"])), None),
        "loanwordCandidate": next((frame["id"] for frame in frames if any(card.get("sourceWord") for card in frame.get("grammarCards", []))), None),
        "pureEnglish": next((frame["id"] for frame in frames if LATIN_RE.search(frame["caption"]["japanese"]) and not JP_RE.search(frame["caption"]["japanese"])), None),
    }


def export_review(frames: list[dict]) -> Path:
    lines = [
        "# ギターと孤独と蒼い惑星｜词卡审核稿", "",
        "整句中文来自 QQ 音乐翻译轨。当前拆词、读音、罗马音、词义和文法结构均为待审核草稿；助词只显示句中功能。", "",
    ]
    for frame in frames:
        caption = frame["caption"]
        lines.extend([
            f"## {frame['id']}　{frame['startMs'] / 1000:.3f}s", "",
            f"歌词：{caption.get('japanese', '')}", "",
            f"暂定中文：{caption.get('translationZh', '')}", "",
            f"分词罗马音：{caption.get('romaji', '')}", "", "待核词卡：", "",
        ])
        for card in frame.get("grammarCards", []):
            source = f"｜外来词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(f"- `{card['token']}`｜读音：{card['reading']}｜罗马音：{card['romaji']}｜暂定：{meaning(card)}｜结构：{card['grammarStructureZh']}{source}")
        lines.append("")
    path = ROOT / "deliverables" / "review" / "guitar-loneliness-blue-planet-review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def main() -> None:
    frames_path = PROJECT / "frames.json"
    shell_backup = PROJECT / "review" / "frames-shell.json"
    shell_backup.parent.mkdir(parents=True, exist_ok=True)
    if not shell_backup.exists():
        shutil.copy2(frames_path, shell_backup)
    document = load(frames_path)
    cache: dict[str, dict] = {}
    frames = [enrich(frame, cache) for frame in document["frames"]]
    document["frames"] = frames
    write(frames_path, document)
    write(PROJECT / "review" / "particle-functions.json", {
        "schemaVersion": 1,
        "usage": "第 4 阶段必须结合语境选择功能；助词卡不显示字典义。",
        "functions": {token: {"functionZh": values[0], "grammarStructureZh": values[1]} for token, values in PARTICLE_FUNCTIONS.items()},
    })

    failures, rendered = render_preflight(frames)
    samples = select_samples(frames)
    preview_paths = {}
    for label, frame_id in samples.items():
        if frame_id and frame_id in rendered:
            destination = PROJECT / "qa" / f"draft-preview-{label}.png"
            shutil.copy2(rendered[frame_id], destination)
            preview_paths[label] = str(destination)
        else:
            preview_paths[label] = None
    review_path = export_review(frames)
    report = {
        "schemaVersion": 1,
        "stage": "draft",
        "result": "passed" if not failures else "failed",
        "frameCount": len(frames),
        "cardCount": sum(len(frame.get("grammarCards", [])) for frame in frames),
        "renderedFrameCount": len(rendered),
        "maxCardCount": max(len(frame.get("grammarCards", [])) for frame in frames),
        "maxCardCountFrame": max(frames, key=lambda frame: len(frame.get("grammarCards", [])))["id"],
        "oneRowGrammarCards": True,
        "meaningMaxLines": 2,
        "selectedSamples": samples,
        "previewPaths": preview_paths,
        "failures": failures,
        "reviewDocument": str(review_path),
    }
    write(PROJECT / "qa" / "layout-report.json", report)
    if failures:
        raise SystemExit(f"Draft layout preflight failed for {len(failures)} frame(s).")
    subprocess.run([sys.executable, str(SKILL / "scripts" / "validate_project.py"), str(ROOT), "--stage", "draft"], check=True)
    state = load(PROJECT / "build-state.json")
    state["stage"] = "draft_ready"
    state["renderAuthorization"] = False
    state.setdefault("notes", []).append("Card draft generated; all automated linguistic fields remain unapproved.")
    write(PROJECT / "build-state.json", state)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
