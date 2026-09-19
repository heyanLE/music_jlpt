#!/usr/bin/env python3
"""Regression tests for lexicon reliability feedback and the kana matching policy.

Both were defeated in an adversarial review: a correction used to clear the
net-rejection cap, repeated accepts could never lift a rejected entry, and a
kana-only match could silently reuse the wrong homophone. These tests pin the
fixed behaviour.

Run:  python test_lexicon_feedback.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from build_lexicon import score_entry  # noqa: E402
from lexicon_match import load_lexicon  # noqa: E402

RESULTS: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append({"case": name, "ok": bool(condition), "detail": detail})


def entry_with(**overrides) -> dict:
    entry = {"humanConfirmed": 0, "projectCount": 1, "dominantGrammar": "名词", "dominantMeaning": "义",
             "ambiguity": {"meaningVariants": 1, "grammarVariants": 1}, "kind": "content", "accepts": 0, "rejects": 0}
    entry.update(overrides)
    return entry


def main() -> None:
    # -- scoring ---------------------------------------------------------------
    rejected_once = score_entry(entry_with(rejects=1))
    rejected_twice = score_entry(entry_with(rejects=2))
    check("one rejection lowers an entry", rejected_once < score_entry(entry_with()), f"{rejected_once}")
    check("two rejections lower it further", rejected_twice < rejected_once, f"{rejected_twice} < {rejected_once}")

    recovered = score_entry(entry_with(rejects=2, accepts=5))
    check("repeat accepts recover a rejected entry", recovered >= 0.85, f"score={recovered}")
    check("net-rejected entry stays low", score_entry(entry_with(rejects=4, accepts=1)) < 0.70,
          f"score={score_entry(entry_with(rejects=4, accepts=1))}")
    check("a correction alone does not clear the cap",
          score_entry(entry_with(rejects=1, accepts=0)) < 0.5,
          "corrections no longer count as accepts in build_lexicon.score_entry")

    # -- kana policy -----------------------------------------------------------
    workspace = Path(tempfile.mkdtemp(prefix="lexicon-test-"))
    try:
        lexicon_dir = workspace / "lexicon"
        lexicon_dir.mkdir(parents=True)
        source = Path(r"C:\project\musicjlpt\lexicon\lexicon.json")
        if source.is_file():
            shutil.copy2(source, lexicon_dir / "lexicon.json")
            lexicon = load_lexicon(lexicon_dir / "lexicon.json")
            kana_reviewed = 0
            kana_auto = 0
            homophone_example = None
            for probe in ("あした", "きみ", "あなた", "いま", "ゆめ"):
                result = lexicon.match_line(probe)
                for span in result["spans"]:
                    if span["kind"] == "match" and span["matchedBy"] == "kana":
                        kana_reviewed += 1
                        if not span["needsReview"]:
                            kana_auto += 1
                        if span.get("homophoneAlternatives") and homophone_example is None:
                            homophone_example = (span["text"], span["surface"], [item["surface"] for item in span["homophoneAlternatives"]])
            check("no kana-only match is ever auto-reused", kana_auto == 0,
                  f"{kana_reviewed} kana matches, {kana_auto} auto")
            check("kana matches expose homophone alternatives", homophone_example is not None,
                  f"example={homophone_example}")

            # -- feedback plumbing -------------------------------------------------
            decisions = workspace / "decisions.json"
            decisions.write_text(json.dumps({
                "project": "sandbox", "wording": "test",
                "entries": [{"surface": "結んで", "outcome": "rejected"},
                            {"surface": "で", "outcome": "corrected", "field": "meaning",
                             "newValue": "提示动作的共同参与者", "context": "二人で"}],
            }, ensure_ascii=False), encoding="utf-8")
            applied = subprocess.run([sys.executable, str(SCRIPTS / "apply_lexicon_feedback.py"), str(workspace),
                                      "--decisions", str(decisions), "--apply"], capture_output=True, text=True)
            check("feedback applies", applied.returncode == 0, applied.stderr.strip()[:150])
            feedback = json.loads((lexicon_dir / "feedback.json").read_text(encoding="utf-8"))
            check("a rejection counts only as a rejection",
                  feedback["entries"]["結んで"]["rejects"] == 1 and feedback["entries"]["結んで"]["accepts"] == 0)
            check("a correction is not counted as an accept",
                  feedback["entries"]["で"]["corrections"] == 1 and feedback["entries"]["で"]["accepts"] == 0)
            overrides = json.loads((lexicon_dir / "overrides.json").read_text(encoding="utf-8"))
            check("net-rejected entry is capped", overrides["entries"]["結んで"].get("reliability") == 0.3)
            check("a correction is stored as a variant, not a replacement",
                  overrides["entries"]["で"]["corrections"][0]["value"] == "提示动作的共同参与者"
                  and "meaning" not in overrides["entries"]["で"])

            unknown = workspace / "unknown.json"
            unknown.write_text(json.dumps({"project": "sandbox", "entries": [{"surface": "存在しない語", "outcome": "accepted"}]},
                                          ensure_ascii=False), encoding="utf-8")
            refused = subprocess.run([sys.executable, str(SCRIPTS / "apply_lexicon_feedback.py"), str(workspace),
                                      "--decisions", str(unknown), "--apply"], capture_output=True, text=True)
            check("feedback for an unknown surface is refused", refused.returncode != 0, refused.stderr.strip()[:120])
        else:
            check("published lexicon is available to test against", False, str(source))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    failures = [result for result in RESULTS if not result["ok"]]
    for result in RESULTS:
        print(f"[{'OK   ' if result['ok'] else 'FAIL '}] {result['case']}" + (f"  ({result['detail']})" if result["detail"] else ""))
    print(json.dumps({"total": len(RESULTS), "failed": len(failures)}, ensure_ascii=False))
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
