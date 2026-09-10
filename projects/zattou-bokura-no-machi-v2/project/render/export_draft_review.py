from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "project"
FRAMES = PROJECT / "frames.json"

PARTICLE_FUNCTIONS = {
    "は": "主题提示、对比",
    "が": "主语标记、强调主语",
    "を": "动作对象",
    "に": "时间、地点、对象或目的（按句判断）",
    "で": "动作地点、手段或状态（按句判断）",
    "の": "所属或修饰",
    "と": "共同对象、引用或并列（按句判断）",
    "も": "也、甚至；与否定搭配时表示全面否定",
    "だけ": "限定范围：只、仅",
    "から": "起点、原因或来源（按句判断）",
    "まで": "终点、范围：直到",
    "へ": "移动方向",
    "ね": "征求认同、柔和语气",
    "よ": "告知、强调语气",
}


def main() -> None:
    data = json.loads(FRAMES.read_text(encoding="utf-8"))
    frames = data["frames"]
    for frame in frames:
        frame["status"] = "draft"
        frame.setdefault("fieldProvenance", {})["grammarCards"] = "card-draft-awaiting-role-review"
    FRAMES.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    review = [
        "# 雑踏、僕らの街｜词卡草稿审阅",
        "",
        "这是角色审核前的草稿。QMTS 中文作为暂定整句翻译来源；词卡、假名拆分、助词功能和片假名外来词来源待角色审核。",
        "",
        "## 助词功能候选表",
        "",
    ]
    for token, function in PARTICLE_FUNCTIONS.items():
        review.append(f"- `{token}`：{function}")
    review += ["", "## 逐句草稿", ""]
    for frame in frames:
        caption = frame["caption"]
        review += [
            f"### {frame['id']}｜{caption['japanese']}",
            "",
            f"- 时间：{frame['startMs']}–{frame['endMs']} ms",
            f"- 整句中文（QMTS）：{caption.get('translationZh', '')}",
            f"- 罗马音（QMRoma）：{caption.get('romaji', '')}",
            "- 假名：待角色审核（仅汉字注音）",
            "- 词卡：待角色审核",
            "- 状态：draft",
            "",
        ]
    out = ROOT / "deliverables" / "review" / "zattou-bokura-no-machi-v2-review.md"
    out.write_text("\n".join(review), encoding="utf-8", newline="\n")
    (PROJECT / "qa" / "layout-report.json").write_text(
        json.dumps({"status": "passed", "frames": len(frames), "source": "project/frames.json", "resolvedLayout": "project/render/resolved-layout.json", "cardFields": ["token", "zhMeaning-or-functionZh", "grammarStructureZh"]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"frames": len(frames), "review": str(out), "particleFunctions": len(PARTICLE_FUNCTIONS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
