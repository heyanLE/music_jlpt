"""Merge the user-authorized multi-role review proposals into frames.json.

The original QRC display text and timings are never modified.  This is a
review-data merge only; it intentionally does not create render authorization.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FRAMES_PATH = ROOT / "frames.json"
PROPOSALS = ROOT / "proposals"
REVIEW_DIR = ROOT / "review"
DELIVERY_REVIEW = ROOT.parent / "deliverables" / "review"
AUTHORITY = "user-authorized-multirole-20260815"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    json.loads(path.read_text(encoding="utf-8"))


def reviewed_card(card: dict) -> dict:
    out = dict(card)
    out["render"] = True
    out["status"] = "human-confirmed"
    out["fieldProvenance"] = {"source": AUTHORITY}
    return out


def early_card(values: list) -> dict:
    # early tuple: token, reading, romaji, meaning/function, pos, field?, sourceWord?
    token, reading, romaji, content, pos = values[:5]
    field = values[5] if len(values) > 5 and values[5] in {"zhMeaning", "functionZh"} else "zhMeaning"
    card = {
        "token": token, "reading": reading, "romaji": romaji,
        "posZh": pos, field: content,
    }
    if len(values) > 6 and values[6]:
        card["sourceWord"] = values[6]
    return reviewed_card(card)


def late_card(values: list) -> dict:
    # late tuple: token, reading, romaji, pos, meaning/function
    if len(values) == 4:
        # The late proposal intentionally omitted redundant romaji for two
        # pure-kana endings in l064.  Supply the verified readings here.
        token, reading, pos, content = values
        romaji = {"だ": "da", "なんて": "nante"}[token]
    else:
        token, reading, romaji, pos, content = values[:5]
    field = "functionZh" if "助词" in pos else "zhMeaning"
    return reviewed_card({
        "token": token, "reading": reading, "romaji": romaji,
        "posZh": pos, field: content,
    })


def set_path(obj: dict, dotted: str, value) -> None:
    target = obj
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def set_provenance(frame: dict, path: str) -> None:
    frame.setdefault("fieldProvenance", {})[path] = {
        "source": AUTHORITY,
        "decision": "采纳全部提案，l042 使用唱读覆盖",
    }


def ruby_runs(cards: list[dict]) -> list[dict]:
    """Store annotation records for actual kanji spans only.

    A token may contain literal kana (e.g. 忘れちゃった).  Those kana are used
    to divide its supplied reading, so no annotation record can cover them.
    """
    runs = []
    for card in cards:
        token = card["token"]
        if any("一" <= ch <= "龯" for ch in token):
            parts = re.findall(r"[一-龯々]+|[^一-龯々]+", token)
            remaining = card["reading"]
            for index, part in enumerate(parts):
                if not re.fullmatch(r"[一-龯々]+", part):
                    if remaining.startswith(part):
                        remaining = remaining[len(part):]
                    continue
                literal_after = ""
                if index + 1 < len(parts) and not re.fullmatch(r"[一-龯々]+", parts[index + 1]):
                    literal_after = parts[index + 1]
                if literal_after and literal_after in remaining:
                    # Use the final occurrence: in 謳う / うたう, the first
                    # う belongs to the kanji while the final う is literal.
                    cut = remaining.rfind(literal_after)
                    reading = remaining[:cut]
                    remaining = remaining[cut + len(literal_after):]
                else:
                    # A fully-kanji token (or an uncertain split): keep the
                    # supplied reading on the kanji span rather than on token.
                    reading, remaining = remaining, ""
                runs.append({
                    "base": part,
                    "reading": reading,
                    "annotationKind": "furigana-kanji-only",
                })
        elif card.get("sourceWord"):
            runs.append({
                "base": token,
                "sourceWord": card["sourceWord"],
                "annotationKind": "loanword-source",
            })
    return runs


def make_review(frames: list[dict]) -> str:
    lines = [
        "# もうどうなってもいいや｜词卡审核版",
        "",
        "本版已按用户授权合并三组联网提案。l042 保留 QRC 原文与时码，使用唱读覆盖；尚未授权渲染。",
        "",
    ]
    for frame in frames:
        c = frame["caption"]
        lines += [f"## {frame['id']}  {c['japanese']}", "", f"- 暂定中文：{c.get('translationZh', '')}"]
        if c.get("readingOverride"):
            lines.append(f"- 唱读覆盖：{c['readingOverride']}")
        if c.get("romaji"):
            lines.append(f"- 罗马音：{c['romaji']}")
        lines.append("")
        for card in frame.get("grammarCards", []):
            meaning = card.get("functionZh", card.get("zhMeaning", ""))
            source = f"（原词：{card['sourceWord']}）" if card.get("sourceWord") else ""
            lines.append(f"- {card['token']}｜{meaning}｜{card.get('posZh', '')}{source}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    source_frames = load(FRAMES_PATH)
    frames = source_frames["frames"]
    by_id = {f["id"]: f for f in frames}
    log = []

    early = load(PROPOSALS / "mou-v2-early-l001-l024.json")
    for proposal in early["proposals"]:
        frame = by_id[proposal["frameId"]]
        for key, value in proposal.get("caption", {}).items():
            frame["caption"][key] = value
            set_provenance(frame, f"caption.{key}")
        frame["grammarCards"] = [early_card(values) for values in proposal["cards"]]
        frame["caption"]["annotationRuns"] = ruby_runs(frame["grammarCards"])
        frame["analysisStatus"] = "human-confirmed"
        set_provenance(frame, "grammarCards")
        log.append({"frameId": frame["id"], "proposal": early["scope"], "fields": ["caption", "grammarCards"]})

    middle = load(PROPOSALS / "mou-v2-middle-l025-l048.json")
    for proposal in middle["proposals"]:
        frame = by_id[proposal["frameId"]]
        changed = []
        for change in proposal["changes"]:
            field, value = change["field"], change["value"]
            if field == "grammarCards":
                value = [reviewed_card(card) for card in value]
                frame["grammarCards"] = value
                frame["caption"]["annotationRuns"] = ruby_runs(value)
            else:
                set_path(frame, field, value)
            set_provenance(frame, field)
            changed.append(field)
        frame["analysisStatus"] = "human-confirmed"
        log.append({"frameId": frame["id"], "proposal": middle["scope"], "fields": changed})

    late = load(PROPOSALS / "mou-v2-late-l049-l072.json")
    for update in late["frameUpdates"]:
        frame = by_id[update["id"]]
        frame["caption"]["translationZh"] = update["translationZh"]
        frame["analysisStatus"] = "human-confirmed"
        set_provenance(frame, "caption.translationZh")
        log.append({"frameId": frame["id"], "proposal": late["scope"], "fields": ["caption.translationZh"]})
    for replacement in late["replaceCards"]:
        frame = by_id[replacement["id"]]
        frame["grammarCards"] = [late_card(values) for values in replacement["cards"]]
        frame["caption"]["annotationRuns"] = ruby_runs(frame["grammarCards"])
        frame["analysisStatus"] = "human-confirmed"
        set_provenance(frame, "grammarCards")
        log.append({"frameId": frame["id"], "proposal": late["scope"], "fields": ["grammarCards"]})

    # Explicit user decision: retain the QRC's stylised source text and timings,
    # but show its sung pronunciation instead of inventing replacement text.
    frame42 = by_id["l042"]
    frame42["caption"]["readingOverride"] = "いち に の さん で こころ らいふる"
    frame42["caption"]["romajiOverride"] = "ichi ni no san de kokoro raifuru"
    frame42["caption"]["pronunciationOverrideScope"] = "display-pronunciation-only; qrc-text-and-timings-preserved"
    set_provenance(frame42, "caption.readingOverride")
    set_provenance(frame42, "caption.romajiOverride")
    log.append({"frameId": "l042", "proposal": "explicit-user-override", "fields": ["caption.readingOverride", "caption.romajiOverride"]})

    write_json(FRAMES_PATH, source_frames)
    frame_sha = hashlib.sha256(FRAMES_PATH.read_bytes()).hexdigest()
    decision = {
        "content": "approved",
        "scope": "all",
        "renderAuthorized": False,
        "frameSha256": frame_sha,
        "userDecision": "采纳全部提案，l042 使用唱读覆盖",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    write_json(REVIEW_DIR / "review-decision.json", decision)
    write_json(REVIEW_DIR / "merge-log.json", {
        "mergedAt": datetime.now(timezone.utc).isoformat(),
        "authority": AUTHORITY,
        "proposalFiles": [p.name for p in sorted(PROPOSALS.glob("*.json"))],
        "changes": log,
        "frameSha256": frame_sha,
    })

    review_text = make_review(frames)
    for path in (REVIEW_DIR / "review.md", DELIVERY_REVIEW / "mou-dou-natte-mo-ii-ya-v2-review.md"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(review_text, encoding="utf-8", newline="\n")

    state_path = ROOT / "build-state.json"
    state = load(state_path)
    state.update({
        "stage": "review_approved",
        "reviewDecision": str((REVIEW_DIR / "review-decision.json").relative_to(ROOT.parent)).replace("\\", "/"),
        "renderAuthorized": False,
        "renderInput": "frames.json",
        "renderInputSha256": frame_sha,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })
    write_json(state_path, state)
    print(json.dumps({"frames": len(frames), "sha256": frame_sha, "stage": state["stage"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
