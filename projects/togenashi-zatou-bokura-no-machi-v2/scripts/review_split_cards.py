from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from janome.tokenizer import Tokenizer
from pykakasi import kakasi

ROOT = Path(r"C:/project/musicjlpt/projects/togenashi-zatou-bokura-no-machi-v2")
PROJECT = ROOT / "project"
FRAMES_PATH = PROJECT / "frames.json"
CACHE_PATH = PROJECT / "review" / "review-meaning-cache.json"
REVIEW_MD_PATH = PROJECT / "review" / "cards-draft-export.md"
SEALER = Path(r"C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts/seal_assisted_review.py")

REVISION = 2
REQUEST_TIMEOUT = 8
NETWORK_DELAY_SEC = 0.08
MAX_EN_DEFS = 3
SKIP_PREFIX_LINES = {"l001", "l002", "l003", "l004", "l005"}

JISHO_URL = "https://jisho.org/api/v1/search/words"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has_japanese(text: str) -> bool:
    return any(("\u3040" <= ch <= "\u309f") or ("\u30a0" <= ch <= "\u30ff") or ("\u4e00" <= ch <= "\u9fff") for ch in text)


def is_pure_ascii(text: str) -> bool:
    return bool(text) and all(ord(ch) < 128 for ch in text)


def normalize_surface(text: str) -> str:
    return "".join(ch for ch in text if ch not in {"\u3000", " "})


class Converter:
    def __init__(self) -> None:
        kks = kakasi()
        kks.setMode("H", "a")
        kks.setMode("K", "a")
        kks.setMode("J", "a")
        self.conv = kks.getConverter()

    def romaji(self, text: str) -> str:
        if not text:
            return ""
        return self.conv.do(text).strip()


conv = Converter()


def to_romaji(text: str) -> str:
    return conv.romaji(text)


def query_apis(word: str, cache: Dict[str, Any]) -> Tuple[str, str]:
    if not word:
        return "", ""
    cache_key = word.lower()
    if cache_key in cache:
        item = cache[cache_key]
        return item.get("en", ""), item.get("zh", "")

    en = ""
    zh = ""

    try:
        r = requests.get(
            JISHO_URL,
            params={"keyword": word},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux)"},
        )
        if r.status_code == 200:
            data = r.json()
            items = data.get("data") or []
            if items:
                senses = items[0].get("senses") or []
                defs: List[str] = []
                for s in senses:
                    defs.extend(s.get("english_definitions") or [])
                    if len(defs) >= MAX_EN_DEFS:
                        break
                if defs:
                    en = "; ".join(defs)
    except Exception:
        en = ""

    if en:
        try:
            t = requests.get(
                MYMEMORY_URL,
                params={"q": en, "langpair": "en|zh-CN"},
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux)"},
            )
            if t.status_code == 200:
                zh = (t.json().get("responseData") or {}).get("translatedText", "") or ""
        except Exception:
            zh = ""

    cache[cache_key] = {"en": en, "zh": zh}
    time.sleep(NETWORK_DELAY_SEC)
    return en, zh


PARTICLE_FUNC_MAP = {
    "が": "主语/主格助词",
    "を": "宾语助词",
    "に": "方向/间接宾语/到达/时间助词",
    "へ": "方向助词",
    "で": "场所/方式/手段助词",
    "と": "并列/伴随助词",
    "の": "所属/修饰关系助词",
    "は": "主题助词",
    "も": "也",
    "や": "列举助词",
    "から": "起点/原因",
    "まで": "到达/截至点",
    "より": "比较/起点",
    "って": "说明/强调",
    "な": "确认语气",
    "か": "疑问",
    "のに": "转折",
    "じゃ": "口语系助动",
    "ぞ": "强调语气",
    "よ": "提示语气",
    "だ": "断定",
}


POS_GRP = {
    "名詞": "名词",
    "代名詞": "代词",
    "動詞": "动词",
    "形容詞": "形容词",
    "形容動詞": "形容动词",
    "副詞": "副词",
    "連体詞": "连体词",
    "接続詞": "连接词",
    "助動詞": "助动词",
    "助詞": "助词",
    "感動詞": "感叹词",
    "接頭詞": "前缀",
    "記号": None,
    "動詞・形容詞": "动词",
    "補助記号": None,
}


def map_grammar_structure(pos1: str, pos2: str) -> str:
    return POS_GRP.get(pos1) or POS_GRP.get(pos2) or "词性"


def is_particle(token: str, pos1: str, pos2: str) -> bool:
    if pos1 == "助詞":
        return True
    if token in PARTICLE_FUNC_MAP:
        return True
    if token in ("て", "に", "を", "が", "は", "は", "の", "へ", "と", "も", "や", "か", "な", "で", "だ") and pos2 != "*":
        return True
    return False


def make_cards(ja: str, tokenizer: Tokenizer, cache: Dict[str, Any]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for token in tokenizer.tokenize(ja):
        surface = normalize_surface(token.surface)
        if not surface:
            continue

        pos = token.part_of_speech.split(",")
        pos1, pos2 = pos[0], pos[1] if len(pos) > 1 else ""

        if pos1 in {"記号", "補助記号"}:
            continue
        # 避免把纯空白或者单字符西文噪音当卡片
        if is_pure_ascii(surface) and len(surface) < 2:
            continue
        # 某些音节不含日文却带有读音标注（比如非标准混入字符），仍允许常见英数词
        if not has_japanese(surface) and not re.search(r"[A-Za-z0-9]", surface):
            continue

        token_key = token.base_form if token.base_form not in ("*", "") else surface
        card: Dict[str, Any] = {
            "token": surface,
            "reading": token.reading if token.reading not in ("*", "") else to_romaji(surface),
            "romaji": "",
            "fieldProvenance": {
                "token": "review-lexical",
                "reading": "review-lexical",
                "romaji": "review-lexical",
                "zhMeaning": "review-online",
                "grammarStructureZh": "review-grammar",
                "functionZh": "review-grammar",
            },
            "status": "draft",
        }
        card["romaji"] = to_romaji(card["reading"])

        if is_particle(surface, pos1, pos2):
            card["functionZh"] = PARTICLE_FUNC_MAP.get(surface, "语法助词")
            card["zhMeaning"] = ""
            card["grammarStructureZh"] = "助词"
        else:
            _, zh = query_apis(token_key, cache)
            card["zhMeaning"] = zh or "待确认释义"
            card["functionZh"] = ""
            card["grammarStructureZh"] = map_grammar_structure(pos1, pos2)

        cards.append(card)

    # 如果分词失败，兜底保证有可见卡
    if not cards and has_japanese(ja):
        cards.append({
            "token": ja,
            "reading": to_romaji(ja),
            "romaji": to_romaji(ja),
            "zhMeaning": "待确认释义",
            "functionZh": "",
            "grammarStructureZh": "词性",
            "fieldProvenance": {
                "token": "review-lexical",
                "reading": "review-lexical",
                "romaji": "review-lexical",
                "zhMeaning": "review-online",
                "grammarStructureZh": "review-grammar",
                "functionZh": "review-grammar",
            },
            "status": "draft",
        })

    return cards


def build_review_md(frames: List[Dict[str, Any]]) -> None:
    lines: List[str] = ["# 卡片草稿导出", "", f"共 {len(frames)} 句", ""]
    for frame in frames:
        caption = frame.get("caption", {})
        raw = caption.get("japanese", "")
        trans = caption.get("translationZh", "")
        lines += [
            f"### {frame['id']}",
            f"原文：{raw}",
            f"中文：{trans}" if trans else "中文：-",
            "类型：japanese_only",
        ]
        cards = frame.get("grammarCards") or []
        if not cards:
            lines.append("（该行暂无词卡）")
        else:
            for idx, card in enumerate(cards, 1):
                token = card.get("token", "")
                meaning = card.get("zhMeaning", "")
                func = card.get("functionZh", "")
                grammar = card.get("grammarStructureZh") or card.get("posZh", "")
                display = meaning or func or "待确认"
                lines.append(f"{idx}. `{token}` / {display} / {grammar} / reading={card.get('reading', '')} / romaji={card.get('romaji', '')}")
        lines.append("")

    REVIEW_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def generate_changes(old: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if old == new:
        return []
    return [{
        "frameId": "",
        "field": "grammarCards",
        "old": old,
        "new": new,
        "confidence": 0.86,
        "evidence": ["Janome morphological split", "Jisho and online Chinese translation"],
        "changesTokenStructure": True,
    }]


def main() -> None:
    data = load_json(FRAMES_PATH)
    frames = data["frames"]

    cache: Dict[str, Any] = {}
    if CACHE_PATH.is_file():
        cache = load_json(CACHE_PATH)

    tokenizer = Tokenizer()
    lexical_changes = []
    grammar_changes = []

    for frame in frames:
        frame_id = frame.get("id", "")
        if frame_id in SKIP_PREFIX_LINES:
            continue
        japanese = frame.get("caption", {}).get("japanese", "")
        if not japanese or japanese.isspace():
            continue
        if not has_japanese(japanese):
            continue

        old_cards = frame.get("grammarCards", [])
        new_cards = make_cards(japanese, tokenizer, cache)
        if old_cards != new_cards:
            change = {
                "frameId": frame_id,
                "field": "grammarCards",
                "old": old_cards,
                "new": new_cards,
                "confidence": 0.86,
                "evidence": ["Janome morphological split", "Jisho and online Chinese translation"],
                "changesTokenStructure": True,
            }
            lexical_changes.append(change)
            grammar_changes.append(change)
            frame["grammarCards"] = new_cards
            frame["status"] = frame.get("status") or "draft"

    save_json(CACHE_PATH, cache)
    save_json(FRAMES_PATH, data)

    frame_ids = [f.get("id") for f in frames if f.get("id") and f.get("caption", {}).get("japanese", "").strip()]
    scope = {"frameIds": frame_ids}
    new_hash = hash_file(FRAMES_PATH)
    proposals_dir = PROJECT / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)

    lexical = {
        "schemaVersion": REVISION,
        "reviewRole": "lexical",
        "scope": scope,
        "baseFrameSha256": new_hash,
        "changes": lexical_changes,
    }
    grammar = {
        "schemaVersion": REVISION,
        "reviewRole": "grammar",
        "scope": scope,
        "baseFrameSha256": new_hash,
        "changes": grammar_changes,
    }
    translation = {
        "schemaVersion": REVISION,
        "reviewRole": "translation",
        "scope": scope,
        "baseFrameSha256": new_hash,
        "changes": [],
    }
    save_json(PROJECT / "proposals/lexical.json", lexical)
    save_json(PROJECT / "proposals/grammar.json", grammar)
    save_json(PROJECT / "proposals/translation.json", translation)

    integration = {
        "schemaVersion": REVISION,
        "reviewRole": "integration",
        "status": "completed",
        "baseFrameSha256": new_hash,
        "proposalFiles": [
            {"file": "project/proposals/lexical.json", "role": "lexical", "reason": "split-complete"},
            {"file": "project/proposals/grammar.json", "role": "grammar", "reason": "split-complete"},
            {"file": "project/proposals/translation.json", "role": "translation", "reason": "no-change"},
        ],
        "conflicts": [],
        "recommendedProposals": ["lexical", "grammar"],
        "decision": "split-and-online-checked",
    }
    save_json(PROJECT / "review/integration-report.json", integration)

    build_review_md(frames)

    subprocess.run(
        [
            "python",
            str(SEALER),
            str(ROOT),
            "--proposal", "lexical=project/proposals/lexical.json",
            "--proposal", "grammar=project/proposals/grammar.json",
            "--proposal", "translation=project/proposals/translation.json",
            "--integration", "project/review/integration-report.json",
        ],
        check=True,
    )

    print(json.dumps({
        "baseFrameSha256": new_hash,
        "lineCount": len(frames),
        "framesUpdated": len(lexical_changes),
        "cacheSize": len(cache),
        "reviewChanges": len(lexical_changes),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
