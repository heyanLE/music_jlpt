from __future__ import annotations

import copy
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def set_path(frame: dict, field: str, value) -> None:
    parts = re.findall(r"[^.\[\]]+|\d+", field)
    target = frame
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list):
        target[int(last)] = copy.deepcopy(value)
    else:
        target[last] = copy.deepcopy(value)


def card_text(card: dict) -> str:
    meaning = card.get("functionZh") or card.get("zhMeaning") or ""
    source = f"；词源 {card['sourceWord']}" if card.get("sourceWord") else ""
    return f"`{card.get('token', '')}`｜{meaning}｜{card.get('grammarStructureZh', '')}{source}"


def main() -> None:
    document = load(PROJECT / "frames.json")
    integration = load(PROJECT / "review" / "integration-report.json")
    proposed = copy.deepcopy(document)
    by_id = {frame["id"]: frame for frame in proposed["frames"]}
    for change in integration["recommendedProposalSet"]["changes"]:
        set_path(by_id[change["frameId"]], change["field"], change["new"])

    attention_frame_ids = set()
    attention_zh = {
        "l020": "已将「待ち＋あぐね」合并为「待ちあぐね」。建议确认结构“复合动词连用形（中顿）”与含义“等得厌倦；等得不耐烦”。",
        "l024": "「に」词卡仅保留句中功能 functionZh，已按词卡契约舍弃竞争提案中的词义字段。",
        "l028": "该译文以 0.91 置信度补出了省略对象“你”：只要思念着你，距离便还不算遥远。",
        "l014、l015": "两句构成跨行片段，暂改为“我透过酒杯／窥望着另一边”，建议连起来审核。",
        "l025、l026": "两句构成跨行片段，暂改为“一路走到今天的我们，如今仿佛已能／跨越过往的一切”。",
        "全局": "有 8 个助词功能按字段归属采用 grammar 角色版本，尽管 translation 角色的竞争措辞置信度略高；下方已逐项公开。",
    }
    for item in integration.get("attentionItems", []):
        if item.get("frameId"):
            attention_frame_ids.add(item["frameId"])
        attention_frame_ids.update(item.get("frameIds", []))
    lower_conflicts = [
        conflict for conflict in integration.get("conflicts", [])
        if conflict.get("resolution", {}).get("selectedBelowCompetingConfidence")
    ]
    attention_frame_ids.update(conflict["frameId"] for conflict in lower_conflicts)

    lines = [
        "# 感情グラス｜多角色联网审核汇总", "",
        "当前内容仍是提案，尚未写入 `project/frames.json`。整句中文按上下文列出；只展开需要人工关注的词卡或冲突。", "",
        f"- 基线帧哈希：`{integration['baseFrameSha256']}`",
        f"- 去冲突建议：{len(integration['recommendedProposalSet']['changes'])} 项",
        f"- 已记录冲突：{len(integration.get('conflicts', []))} 项",
        f"- 需要人工关注：{len(integration.get('attentionItems', []))} 类", "",
        "## 每句暂定中文", "",
        "| 帧 | 日文 | 多角色暂定中文 |", "| --- | --- | --- |",
    ]
    for frame in proposed["frames"]:
        caption = frame["caption"]
        lines.append(f"| {frame['id']} | {caption.get('japanese', '')} | {caption.get('translationZh', '')} |")

    lines.extend(["", "## 待人工关注", ""])
    for item in integration.get("attentionItems", []):
        ids = [item["frameId"]] if item.get("frameId") else item.get("frameIds", [])
        label = "、".join(ids) if ids else "全局"
        lines.append(f"### {label}")
        lines.append("")
        lines.append(f"- {attention_zh.get(label, item['item'])}")
        for frame_id in ids:
            frame = by_id[frame_id]
            lines.append(f"- 暂定中文：{frame['caption'].get('translationZh', '')}")
            if frame_id in {"l020", "l024"}:
                lines.append("- 相关词卡：")
                lines.extend(f"  - {card_text(card)}" for card in frame.get("grammarCards", []))
        lines.append("")

    lines.extend(["## 所有低于竞争项置信度的归属冲突", ""])
    if not lower_conflicts:
        lines.append("- 无。")
    for conflict in lower_conflicts:
        resolution = conflict["resolution"]
        alternatives = "；".join(
            f"{proposal['role']}={proposal['new']}（{proposal['confidence']:.2f}）"
            for proposal in conflict["proposals"]
        )
        lines.append(
            f"- `{conflict['frameId']} {conflict['field']}`：采用 {resolution['selectedRole']} 的“{resolution['selectedNew']}”"
            f"（{resolution['selectedConfidence']:.2f}）；竞争项：{alternatives}"
        )

    lines.extend(["", "## 审核结论", "", "三角色与整合审计均未修改正式帧。若整体采纳，将只合并本报告绑定的 259 项建议，并重新进行词卡版式验证。", ""])
    output = ROOT / "deliverables" / "review" / "kanjou-glass-assisted-review.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(output), "lines": len(proposed["frames"]), "attentionFrames": sorted(attention_frame_ids)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
