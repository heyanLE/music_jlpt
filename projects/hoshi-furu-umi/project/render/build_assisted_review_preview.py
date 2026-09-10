from __future__ import annotations

import copy
import json
import re
import shutil
import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = Path(r"C:/Users/eke_l/.codex/skills/japanese-song-study-video/scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))

from render_video import ForegroundRenderer  # noqa: E402


PART_RE = re.compile(r"^([^\[\]]+)(?:\[(\d+)\])?$")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def resolve_parent(frame: dict, field: str):
    parts = field.split(".")
    current = frame
    for raw in parts[:-1]:
        match = PART_RE.fullmatch(raw)
        if not match:
            raise ValueError(f"Unsupported field path segment: {raw}")
        key, index = match.group(1), match.group(2)
        current = current[key]
        if index is not None:
            current = current[int(index)]
    final = PART_RE.fullmatch(parts[-1])
    if not final:
        raise ValueError(f"Unsupported final field path: {parts[-1]}")
    return current, final.group(1), final.group(2)


def get_value(frame: dict, field: str):
    parent, key, index = resolve_parent(frame, field)
    value = parent[key]
    return value[int(index)] if index is not None else value


def set_value(frame: dict, field: str, value) -> None:
    parent, key, index = resolve_parent(frame, field)
    if index is None:
        parent[key] = copy.deepcopy(value)
    else:
        parent[key][int(index)] = copy.deepcopy(value)


def meaning(card: dict) -> str:
    return card.get("functionZh") or card.get("zhMeaning") or ""


def main() -> None:
    document = load(PROJECT / "project" / "frames.json")
    proposed = copy.deepcopy(document)
    frame_map = {frame["id"]: frame for frame in proposed["frames"]}
    integration = load(PROJECT / "project" / "review" / "integration-report.json")
    apply_errors = []
    for change in integration["recommendedChanges"]:
        frame = frame_map[change["frameId"]]
        current = get_value(frame, change["field"])
        if current != change["old"]:
            apply_errors.append(
                {
                    "frameId": change["frameId"],
                    "field": change["field"],
                    "expected": change["old"],
                    "actual": current,
                }
            )
            continue
        set_value(frame, change["field"], change["new"])
    if apply_errors:
        raise SystemExit(f"Integration proposal failed old-value validation: {len(apply_errors)}")

    proposed["reviewStatus"] = "assisted-review-proposal-only"
    proposed_path = PROJECT / "project" / "review" / "proposed-frames.json"
    write(proposed_path, proposed)

    renderer = ForegroundRenderer(PROJECT, width=1920, height=1080)
    renderer.frames = frame_map
    states = PROJECT / "project" / "qa" / "assisted-review-preview" / "states"
    states.mkdir(parents=True, exist_ok=True)
    failures = []
    rendered = {}
    for frame in proposed["frames"]:
        path = states / f"{frame['id']}.png"
        try:
            renderer.render(frame["id"], active_index=None, output=path, cover_visible=True)
            rendered[frame["id"]] = str(path)
        except Exception as exc:
            failures.append({"frameId": frame["id"], "error": str(exc)})

    attention_map = {item["frameId"]: item for item in integration.get("attentionFrames", [])}
    preview_paths = {}
    preview_root = PROJECT / "project" / "qa" / "assisted-review-preview"
    for frame_id in attention_map:
        if frame_id not in rendered:
            continue
        destination = preview_root / f"attention-{frame_id}.png"
        shutil.copy2(rendered[frame_id], destination)
        preview_paths[frame_id] = str(destination)

    lines = [
        "# 星降る海 · 多角色联网复审提案",
        "",
        "> 本文档是尚未采纳的提案预览。原 `project/frames.json` 未修改，也未获得最终渲染授权。",
        "",
        "## 全部 40 句暂定中文",
        "",
        "| 帧 | 日文 | 暂定中文 |",
        "| --- | --- | --- |",
    ]
    for frame in proposed["frames"]:
        japanese = frame["caption"]["japanese"].replace("|", "\\|")
        chinese = frame["caption"].get("translationZh", "").replace("|", "\\|")
        lines.append(f"| {frame['id']} | {japanese} | {chinese} |")

    lines.extend(["", "## 需要人工关注的词卡与字段", ""])
    for frame in proposed["frames"]:
        frame_id = frame["id"]
        if frame_id not in attention_map:
            continue
        attention = attention_map[frame_id]
        lines.extend(
            [
                f"### {frame_id} · {frame['caption']['japanese']}",
                "",
                f"暂定中文：{frame['caption'].get('translationZh', '')}",
                "",
                f"罗马音：{frame['caption'].get('romaji', '')}",
                "",
                "关注点：" + "；".join(attention.get("issues", [])),
                "",
                "建议：" + attention.get("recommendation", ""),
                "",
                "词卡：",
                "",
            ]
        )
        for card in frame.get("grammarCards", []):
            annotation = f"／外来词源：{card['sourceWord']}" if card.get("sourceWord") else ""
            lines.append(
                f"- `{card['token']}`｜{card.get('reading', '')}｜{card.get('romaji', '')}{annotation}｜{meaning(card)}｜{card.get('grammarStructureZh', '')}"
            )
        lines.append("")

    review_path = PROJECT / "deliverables" / "review" / "hoshi-furu-umi-assisted-review.md"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    max_cards_frame = max(proposed["frames"], key=lambda item: len(item.get("grammarCards", [])))
    report = {
        "schemaVersion": 1,
        "stage": "assisted-review-proposal-preview",
        "result": "passed" if not failures else "failed",
        "proposalOnly": True,
        "recommendedChangeCount": len(integration["recommendedChanges"]),
        "frameCount": len(proposed["frames"]),
        "renderedFrameCount": len(rendered),
        "maxCardCount": len(max_cards_frame.get("grammarCards", [])),
        "maxCardCountFrame": max_cards_frame["id"],
        "attentionFrames": list(attention_map),
        "previewPaths": preview_paths,
        "failures": failures,
        "proposedFrames": str(proposed_path),
        "reviewDocument": str(review_path),
    }
    write(PROJECT / "project" / "qa" / "assisted-review-layout-report.json", report)
    if failures:
        raise SystemExit(f"Assisted-review layout failed: {len(failures)} frame(s)")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
