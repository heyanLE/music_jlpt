"""Proposal-only audit: replace suffix-only glosses on compound cards.

This script only writes project/proposals/compound-card-second.json.  It never
mutates frames.json or caption.translationZh.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRAMES = ROOT / "project" / "frames.json"
OUT = ROOT / "project" / "proposals" / "compound-card-second.json"


# Each meaning deliberately covers the *whole displayed token*, not merely the
# final auxiliary, particle, or inflection.  Repeated lyric lines are included
# individually so a later merge remains line-local and deterministic.
PATCHES: dict[str, dict[str, dict[str, str]]] = {
    "l018": {"笑っていくよ": {"functionZh": "笑着继续走下去；会一直笑下去", "grammarStructureZh": "动词て形＋いく＋终助词"}},
    "l020": {
        "忘れたって": {"functionZh": "即使忘了也…", "grammarStructureZh": "动词过去式＋たって"},
        "消えやしない": {"zhMeaning": "绝不会消失", "grammarStructureZh": "动词否定强调"},
    },
    "l022": {"塗り替えていくよ": {"functionZh": "会不断改写；彻底改变下去", "grammarStructureZh": "动词て形＋いく＋终助词"}},
    "l024": {
        "輝きになって": {"functionZh": "变成光辉；化作光芒", "grammarStructureZh": "名词＋に＋なるて形"},
        "残っている": {"functionZh": "仍然留存着；还保留着", "grammarStructureZh": "动词て形＋いる"},
    },
    "l026": {"だったんだろうな": {"functionZh": "究竟是…呢；想必是…吧", "grammarStructureZh": "断定过去式＋のだ＋推量＋な"}},
    "l028": {"伸ばしている": {"functionZh": "正延伸着；正拉长着", "grammarStructureZh": "动词て形＋いる"}},
    "l032": {"会ってから": {"functionZh": "见面之后；相会后再…", "grammarStructureZh": "动词て形＋から"}},
    "l037": {"泣かなくなっても": {"functionZh": "即使变得不再哭泣也…", "grammarStructureZh": "动词否定＋なるて形＋も"}},
    "l040": {
        "忘れたって": {"functionZh": "即使忘了也…", "grammarStructureZh": "动词过去式＋たって"},
        "消えやしない": {"zhMeaning": "绝不会消失", "grammarStructureZh": "动词否定强调"},
    },
    "l042": {"あったんだろうな": {"functionZh": "一定曾有过吧；想必存在过吧", "grammarStructureZh": "动词过去式＋のだ＋推量＋な"}},
    "l043": {"なんだろうけど": {"functionZh": "大概是…吧，不过…", "grammarStructureZh": "断定＋推量＋けど"}},
    "l046": {"出会った": {"zhMeaning": "相遇了；邂逅了", "grammarStructureZh": "动词过去式"}},
    "l050": {"どうか": {"zhMeaning": "怎么样；是否如何", "grammarStructureZh": "疑问副词"}},
    "l053": {"泣かなくなっても": {"functionZh": "即使变得不再哭泣也…", "grammarStructureZh": "动词否定＋なるて形＋も"}},
    "l054": {"笑っていくよ": {"functionZh": "笑着继续走下去；会一直笑下去", "grammarStructureZh": "动词て形＋いく＋终助词"}},
    "l056": {
        "忘れたって": {"functionZh": "即使忘了也…", "grammarStructureZh": "动词过去式＋たって"},
        "消えやしない": {"zhMeaning": "绝不会消失", "grammarStructureZh": "动词否定强调"},
    },
}


def changed_cards(cards: list[dict], changes: dict[str, dict[str, str]]) -> list[dict]:
    result = deepcopy(cards)
    found = set()
    for card in result:
        patch = changes.get(card["token"])
        if not patch:
            continue
        found.add(card["token"])
        # Cards have exactly one of zhMeaning/functionZh.
        card.pop("zhMeaning", None)
        card.pop("functionZh", None)
        card.update(patch)
        card["status"] = "assisted-proposal"
        provenance = card.setdefault("fieldProvenance", {})
        provenance["meaningOrFunction"] = "compound-card second review proposal"
        provenance["grammarStructureZh"] = "compound-card second review proposal"
    missing = set(changes) - found
    if missing:
        raise ValueError(f"Cards absent from frame: {sorted(missing)}")
    return result


raw = FRAMES.read_bytes()
document = json.loads(raw)
by_id = {frame["id"]: frame for frame in document["frames"]}
changes = []
for frame_id, patch in PATCHES.items():
    frame = by_id[frame_id]
    old = frame["grammarCards"]
    new = changed_cards(old, patch)
    changes.append({
        "frameId": frame_id,
        "field": "grammarCards",
        "old": old,
        "new": new,
        "confidence": 0.98,
        "evidence": [
            "对每个长词/合并词按完整显示 token 重写释义；不再只说明末尾助动词、助词或活用。",
            "小学馆《デジタル大辞泉》对塗り替える释义包含“改成完全不同的东西、更新”，与本句“塗り替えていく”相符：https://dictionary.goo.ne.jp/word/%E5%A1%97%E6%9B%BF%E3%81%88%E3%82%8B/",
            "小学馆《デジタル大辞泉》与活用规则：ている表示进行/结果持续，ていく表示动作、变化向后持续；释义结合当前整词和上下文确定。",
        ],
        "changesTokenStructure": False,
        "doesNotModify": ["caption.translationZh"],
    })

proposal = {
    "schemaVersion": 2,
    "reviewRole": "compound-card-second",
    "baseFrameSha256": hashlib.sha256(raw).hexdigest(),
    "scope": {
        "allowedFields": ["grammarCards"],
        "forbiddenFields": ["caption.translationZh", "caption.japanese", "caption.furigana", "caption.romaji"],
        "policy": "仅修正长词和合并词卡的释义/结构；释义必须覆盖完整 token，不触碰 QMTS 整句中文。",
    },
    "sources": [
        {"title": "goo 国語辞書・デジタル大辞泉（小学館）", "url": "https://dictionary.goo.ne.jp/word/%E5%A1%97%E6%9B%BF%E3%81%88%E3%82%8B/"},
        {"title": "日本語教育用标准活用规则", "note": "ている、ていく、たって、なくなる、んだろう等的组合以当前完整词卡和冻结歌词上下文复核。"},
    ],
    "changes": changes,
}
OUT.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {OUT} with {len(changes)} frame-local changes; base={proposal['baseFrameSha256']}")
