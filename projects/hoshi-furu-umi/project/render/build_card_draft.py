from __future__ import annotations

import copy
import json
import re
import shutil
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
WORKSPACE = PROJECT.parents[1]
LOCAL_SITE = PROJECT / "project" / "work" / "python-site"
SKILL_ROOT = Path(r"C:/Users/eke_l/.codex/skills/japanese-song-study-video")

sys.path.insert(0, str(LOCAL_SITE))
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from pykakasi import kakasi  # noqa: E402
from sudachipy import dictionary, tokenizer  # noqa: E402
from render_video import ForegroundRenderer  # noqa: E402


KANJI_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff々〆ヵヶ]+")
JP_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff々〆ヵヶ]")
LATIN_RE = re.compile(r"[A-Za-z]")
KANA_RE = re.compile(r"[\u3040-\u30ff]")

PARTICLE_FUNCTIONS = {
    "は": "提示主题",
    "が": "标记主语",
    "を": "标记宾语",
    "に": "对象/方向/时间",
    "で": "场所/手段/原因",
    "と": "共同/引用",
    "の": "所属/修饰",
    "も": "也/追加",
    "へ": "表示方向",
    "から": "起点/原因",
    "まで": "终点/范围",
    "や": "不完全列举",
    "ね": "确认/感叹",
    "よ": "告知/强调",
    "さ": "强调语气",
    "か": "疑问/不确定",
    "って": "引用/提示",
    "ばかり": "限定/偏向",
    "だけ": "限定范围",
}

POS_ZH = {
    "名詞": "名词",
    "代名詞": "代词",
    "動詞": "动词",
    "形容詞": "い形容词",
    "形状詞": "な形容词",
    "副詞": "副词",
    "連体詞": "连体词",
    "接続詞": "连词",
    "助詞": "助词",
    "助動詞": "助动词",
    "感動詞": "感叹词",
    "接頭辞": "前缀",
    "接尾辞": "后缀",
}

PARTICLE_PRONUNCIATION = {"は": "わ", "へ": "え", "を": "お"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def katakana_to_hiragana(text: str) -> str:
    chars = []
    for char in text:
        code = ord(char)
        if 0x30A1 <= code <= 0x30F6:
            chars.append(chr(code - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


KKS = kakasi()


def to_romaji(reading: str, surface: str = "") -> str:
    spoken = PARTICLE_PRONUNCIATION.get(surface, reading)
    result = "".join(part.get("hepburn", "") for part in KKS.convert(spoken))
    return re.sub(r"\s+", "", result).lower()


TOKENIZER = dictionary.Dictionary().create()


def is_learning_token(surface: str, pos0: str) -> bool:
    if pos0 in {"空白", "補助記号"}:
        return False
    if not JP_RE.search(surface):
        return False
    if LATIN_RE.search(surface) and not JP_RE.search(surface):
        return False
    return True


def raw_tokens(text: str) -> list[dict]:
    result: list[dict] = []
    for morpheme in TOKENIZER.tokenize(text, tokenizer.Tokenizer.SplitMode.C):
        surface = morpheme.surface()
        pos = morpheme.part_of_speech()
        pos0 = pos[0]
        if not is_learning_token(surface, pos0):
            continue
        reading = katakana_to_hiragana(morpheme.reading_form())
        if not reading or reading == "*":
            reading = katakana_to_hiragana(surface)
        result.append(
            {
                "surface": surface,
                "reading": reading,
                "pos0": pos0,
                "pos": list(pos),
                "dictionaryForm": morpheme.dictionary_form(),
                "merged": False,
            }
        )
    return result


def should_merge(previous: dict, current: dict) -> bool:
    cur_surface = current["surface"]
    cur_pos = current["pos0"]
    prev_pos = previous["pos0"]
    prev_surface = previous["surface"]

    if cur_pos == "助動詞" and prev_pos in {"動詞", "形容詞", "助動詞"}:
        return True
    if cur_surface in {"て", "で"} and cur_pos == "助詞" and prev_pos in {"動詞", "形容詞"}:
        return True
    if cur_surface in {"いる", "いく", "くる"} and prev_surface.endswith(("て", "で")):
        return True
    if cur_surface in {"ない", "た", "だ", "ます", "れる", "られる", "せる", "させる"} and prev_pos in {
        "動詞",
        "形容詞",
        "助動詞",
    }:
        return True
    if cur_surface == "に" and prev_surface == "よう":
        return True
    if cur_surface == "だ" and prev_surface == "ん":
        return True
    return False


def merge_tokens(tokens: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for current in tokens:
        if merged and should_merge(merged[-1], current):
            previous = merged[-1]
            previous["surface"] += current["surface"]
            previous["reading"] += current["reading"]
            previous["merged"] = True
            previous.setdefault("mergedParts", []).append(
                {"surface": current["surface"], "pos0": current["pos0"]}
            )
            continue
        merged.append(copy.deepcopy(current))
    return merged


def card_from_token(token: dict) -> dict:
    surface = token["surface"]
    reading = token["reading"]
    pos0 = token["pos0"]
    grammar = POS_ZH.get(pos0, "词性待复核")
    if token.get("merged"):
        grammar += "（活用）"

    card = {
        "token": surface,
        "reading": reading,
        "romaji": to_romaji(reading, surface),
        "grammarStructureZh": grammar,
        "dictionaryForm": token.get("dictionaryForm", surface),
        "fieldProvenance": {
            "segmentation": "SudachiPy 0.6.11 + sudachidict_core 20260723",
            "reading": "SudachiPy 0.6.11 + sudachidict_core 20260723",
            "romaji": "pykakasi 2.3.0",
            "meaning": "phase-3 unresolved draft",
            "grammarStructure": "Sudachi POS draft",
        },
        "status": "auto-draft-needs-assisted-review",
        "reviewRequired": True,
        "render": True,
    }
    if surface == "んだ":
        card["functionZh"] = "说明/强调语气"
        card["grammarStructureZh"] = "んだ（说明语气）"
        card["fieldProvenance"]["meaning"] = "deterministic fixed-expression draft"
    elif pos0 == "助詞":
        card["functionZh"] = PARTICLE_FUNCTIONS.get(surface, "功能待复核")
        card["fieldProvenance"]["meaning"] = "project particle function table"
    else:
        card["zhMeaning"] = "待联网复核"
    return card


def furigana_for_card(card: dict, lyric: str, search_start: int) -> tuple[list[dict], int]:
    token = card["token"]
    token_pos = lyric.find(token, search_start)
    if token_pos < 0:
        token_pos = lyric.find(token)
    next_search = search_start if token_pos < 0 else token_pos + len(token)
    if token_pos < 0 or not KANJI_RE.search(token):
        return [], next_search

    runs = list(KANJI_RE.finditer(token))
    if len(runs) != 1:
        return [], next_search
    run = runs[0]
    reading = card["reading"]
    prefix = token[: run.start()]
    suffix = token[run.end() :]

    if prefix and KANA_RE.fullmatch(prefix):
        prefix_h = katakana_to_hiragana(prefix)
        if reading.startswith(prefix_h):
            reading = reading[len(prefix_h) :]
    if suffix and KANA_RE.fullmatch(suffix):
        suffix_h = katakana_to_hiragana(suffix)
        if reading.endswith(suffix_h):
            reading = reading[: -len(suffix_h)]

    if not reading:
        return [], next_search
    return (
        [
            {
                "token": token,
                "base": run.group(0),
                "reading": reading,
                "tokenStart": token_pos,
                "baseStart": token_pos + run.start(),
            }
        ],
        next_search,
    )


def enrich_frame(frame: dict, cache: dict[str, dict]) -> dict:
    result = copy.deepcopy(frame)
    caption = result.setdefault("caption", {})
    lyric = caption.get("japanese", "")
    if lyric in cache:
        learned = copy.deepcopy(cache[lyric])
    else:
        tokens = merge_tokens(raw_tokens(lyric))
        cards = [card_from_token(token) for token in tokens]
        search_start = 0
        furigana: list[dict] = []
        for card in cards:
            entries, search_start = furigana_for_card(card, lyric, search_start)
            furigana.extend(entries)
        learned = {
            "cards": cards,
            "furigana": furigana,
            "romaji": " ".join(card["romaji"] for card in cards if card["romaji"]),
        }
        cache[lyric] = copy.deepcopy(learned)

    if caption.get("romaji"):
        caption["sourceRomaji"] = caption["romaji"]
    caption["romaji"] = learned["romaji"]
    caption["furigana"] = learned["furigana"]
    result["grammarCards"] = learned["cards"]
    result["analysisStatus"] = "phase-3-auto-draft"
    result["status"] = "draft"
    result["reviewRequired"] = True
    result.setdefault("fieldProvenance", {})["grammarCards"] = (
        "Sudachi deterministic draft; meanings pending assisted review"
    )
    result["fieldProvenance"]["translationZh"] = "QQ Music qmts source"
    return result


def meaning_of(card: dict) -> str:
    return card.get("functionZh") or card.get("zhMeaning") or ""


def render_all(frames: list[dict]) -> tuple[list[dict], dict[str, str]]:
    output_dir = PROJECT / "project" / "qa" / "draft-layout" / "states"
    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = ForegroundRenderer(PROJECT, width=1920, height=1080)
    failures: list[dict] = []
    paths: dict[str, str] = {}
    for frame in frames:
        frame_id = frame["id"]
        path = output_dir / f"{frame_id}.png"
        try:
            renderer.render(frame_id, active_index=None, output=path, cover_visible=True)
            paths[frame_id] = str(path)
        except Exception as exc:  # visual preflight must report every failure
            failures.append({"frameId": frame_id, "error": str(exc)})
    return failures, paths


def select_samples(frames: list[dict]) -> dict[str, str | None]:
    longest_lyric = max(frames, key=lambda frame: len(frame["caption"]["japanese"]))
    max_cards = max(frames, key=lambda frame: len(frame.get("grammarCards", [])))
    longest_meaning = max(
        frames,
        key=lambda frame: max([len(meaning_of(card)) for card in frame.get("grammarCards", [])] or [0]),
    )
    mixed = next(
        (frame for frame in frames if LATIN_RE.search(frame["caption"]["japanese"])),
        None,
    )
    katakana = next(
        (frame for frame in frames if re.search(r"[\u30a1-\u30fa]", frame["caption"]["japanese"])),
        None,
    )
    pure_english = next(
        (
            frame
            for frame in frames
            if LATIN_RE.search(frame["caption"]["japanese"])
            and not JP_RE.search(frame["caption"]["japanese"])
        ),
        None,
    )
    return {
        "longestLyric": longest_lyric["id"],
        "maximumCardCount": max_cards["id"],
        "longestMeaningOrFunction": longest_meaning["id"],
        "mixedJapaneseEnglish": mixed["id"] if mixed else None,
        "loanwordCandidate": katakana["id"] if katakana else None,
        "pureEnglish": pure_english["id"] if pure_english else None,
    }


def copy_samples(samples: dict[str, str | None], rendered: dict[str, str]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    qa_dir = PROJECT / "project" / "qa"
    for label, frame_id in samples.items():
        if not frame_id or frame_id not in rendered:
            result[label] = None
            continue
        destination = qa_dir / f"draft-preview-{label}.png"
        shutil.copy2(rendered[frame_id], destination)
        result[label] = str(destination)
    return result


def write_review_markdown(frames: list[dict]) -> Path:
    lines = [
        "# 星降る海 · 词卡审核稿",
        "",
        "说明：整句中文来自 QQ 音乐 qmts；词义与词性为第 3 阶段自动草稿，尚未联网复审。英语不生成词卡、假名或罗马音。",
        "",
    ]
    for frame in frames:
        caption = frame["caption"]
        lines.extend(
            [
                f"## {frame['id']} · {frame['startMs'] / 1000:.3f}s",
                "",
                f"日文：{caption.get('japanese', '')}",
                "",
                f"暂定中文（QQ音乐）：{caption.get('translationZh', '')}",
                "",
                f"罗马音：{caption.get('romaji', '')}",
                "",
                "待核词卡：",
                "",
            ]
        )
        cards = frame.get("grammarCards", [])
        if not cards:
            lines.append("- 无（纯英语或无学习词项）")
        for card in cards:
            lines.extend(
                [
                    f"- `{card['token']}`｜{card.get('reading', '')}｜{card.get('romaji', '')}",
                    f"  - 暂定：{meaning_of(card)}",
                    f"  - 结构：{card.get('grammarStructureZh', '')}",
                ]
            )
        lines.append("")
    destination = PROJECT / "deliverables" / "review" / "hoshi-furu-umi-review.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def main() -> None:
    frames_path = PROJECT / "project" / "frames.json"
    shell_backup = PROJECT / "project" / "review" / "frames-shell.json"
    shell_backup.parent.mkdir(parents=True, exist_ok=True)
    if not shell_backup.exists():
        shutil.copy2(frames_path, shell_backup)

    frames_document = read_json(frames_path)
    frames = frames_document.get("frames", frames_document) if isinstance(frames_document, dict) else frames_document
    cache: dict[str, dict] = {}
    enriched = [enrich_frame(frame, cache) for frame in frames]
    if isinstance(frames_document, dict) and "frames" in frames_document:
        frames_document["frames"] = enriched
        write_json(frames_path, frames_document)
    else:
        write_json(frames_path, enriched)

    write_json(
        PROJECT / "project" / "review" / "particle-functions.json",
        {
            "schemaVersion": "1.0",
            "description": "助词卡片功能候选表；第 4 阶段需结合上下文复核。",
            "functions": PARTICLE_FUNCTIONS,
        },
    )

    failures, rendered = render_all(enriched)
    samples = select_samples(enriched)
    preview_paths = copy_samples(samples, rendered)
    review_path = write_review_markdown(enriched)
    max_cards = max(len(frame.get("grammarCards", [])) for frame in enriched)
    max_frame = max(enriched, key=lambda frame: len(frame.get("grammarCards", [])))["id"]
    report = {
        "schemaVersion": "1.0",
        "stage": "draft",
        "result": "passed" if not failures else "failed",
        "frameCount": len(enriched),
        "renderedFrameCount": len(rendered),
        "maxCardCount": max_cards,
        "maxCardCountFrame": max_frame,
        "oneRowGrammarCards": True,
        "meaningMaxLines": 2,
        "mixedEnglishSkipsCards": True,
        "selectedSamples": samples,
        "previewPaths": preview_paths,
        "failures": failures,
        "reviewDocument": str(review_path),
    }
    write_json(PROJECT / "project" / "qa" / "layout-report.json", report)
    if failures:
        raise SystemExit(f"Draft layout preflight failed for {len(failures)} frame(s).")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
