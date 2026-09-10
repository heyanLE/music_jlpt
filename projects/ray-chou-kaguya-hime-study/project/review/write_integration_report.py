import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAMES_PATH = ROOT / "frames.json"
PROPOSALS = {role: ROOT / "proposals" / f"{role}.json" for role in ("lexical", "grammar", "translation")}
OUTPUT = ROOT / "review" / "integration-report.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_path(obj, path: str):
    value = obj
    normalized = path.replace("[", ".").replace("]", "")
    for part in normalized.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def is_card_path(path: str) -> bool:
    return path.startswith("grammarCards.") or path.startswith("grammarCards[")


def card_index(path: str) -> int:
    normalized = path.replace("[", ".").replace("]", "")
    return int(normalized.split(".")[1])


def main():
    base_sha = sha256(FRAMES_PATH)
    frame_list = json.loads(FRAMES_PATH.read_text(encoding="utf-8"))["frames"]
    frames = {frame["id"]: frame for frame in frame_list}
    proposals = {role: json.loads(path.read_text(encoding="utf-8")) for role, path in PROPOSALS.items()}

    contract_issues = []
    for role, proposal in proposals.items():
        if proposal.get("baseFrameSha256") != base_sha:
            contract_issues.append({"role": role, "type": "base-frame-sha-mismatch"})
        scope = set(proposal.get("scope", {}).get("frameIds", []))
        for change in proposal.get("changes", []):
            fid = change.get("frameId")
            if fid not in frames:
                contract_issues.append({"role": role, "type": "unknown-frame", "frameId": fid})
                continue
            if fid not in scope:
                contract_issues.append({"role": role, "type": "out-of-scope-change", "frameId": fid})
            try:
                if get_path(frames[fid], change["field"]) != change.get("old"):
                    contract_issues.append({"role": role, "type": "stale-old-value", "frameId": fid, "field": change["field"]})
            except KeyError:
                # Adding a missing optional field (for example functionZh or
                # zhMeaning) is valid only when the proposal explicitly records
                # the old value as null.
                if change.get("old") is not None:
                    contract_issues.append({"role": role, "type": "stale-old-value", "frameId": fid, "field": change["field"]})
            except (IndexError, TypeError, ValueError):
                contract_issues.append({"role": role, "type": "invalid-field-path", "frameId": fid, "field": change.get("field")})

    lexical_arrays = {
        change["frameId"]: change["new"]
        for change in proposals["lexical"]["changes"]
        if change["field"] == "grammarCards"
    }
    grammar_card_changes = [c for c in proposals["grammar"]["changes"] if is_card_path(c["field"])]
    translation_card_changes = [c for c in proposals["translation"]["changes"] if is_card_path(c["field"])]

    # A draft card index cannot survive lexical phrase merges. Count every later card
    # change that cannot be mapped directly to exactly one same-token card.
    unmappable = []
    for role, changes in (("grammar", grammar_card_changes), ("translation", translation_card_changes)):
        for change in changes:
            fid = change["frameId"]
            if fid not in lexical_arrays:
                continue
            index = card_index(change["field"])
            old_token = frames[fid]["grammarCards"][index]["token"]
            destinations = [card for card in lexical_arrays[fid] if card["token"] == old_token]
            if len(destinations) != 1:
                unmappable.append({"role": role, "frameId": fid, "field": change["field"], "draftToken": old_token})

    # Repeated Japanese rows must not acquire different bundled cards or line translations.
    repeated = defaultdict(list)
    for frame in frame_list:
        repeated[frame["caption"]["japanese"]].append(frame["id"])
    repeated_conflicts = []
    translation_lookup = {(c["frameId"], c["field"]): c["new"] for c in proposals["translation"]["changes"]}
    for ids in repeated.values():
        if len(ids) < 2:
            continue
        lexical_versions = [lexical_arrays.get(fid, frames[fid]["grammarCards"]) for fid in ids]
        if len({json.dumps(value, ensure_ascii=False, sort_keys=True) for value in lexical_versions}) > 1:
            repeated_conflicts.append({"type": "repeated-line-card-inconsistency", "frameIds": ids})
        translations = [translation_lookup.get((fid, "caption.translationZh"), frames[fid]["caption"]["translationZh"]) for fid in ids]
        if len(set(translations)) > 1:
            repeated_conflicts.append({"type": "repeated-line-translation-inconsistency", "frameIds": ids})

    protected = ["mv-p001", "mv-p002"]
    protected_touch = [
        {"role": role, "frameId": change["frameId"], "field": change["field"]}
        for role, proposal in proposals.items()
        for change in proposal["changes"]
        if change["frameId"] in protected
    ]

    conflicts = []
    if contract_issues:
        conflicts.append({"severity": "high", "type": "proposal-contract-issue", "detail": contract_issues,
                          "resolution": "Regenerate affected proposal before integration."})
    if unmappable:
        conflicts.append({
            "severity": "high",
            "type": "structural-index-conflict",
            "frames": sorted({item["frameId"] for item in unmappable}),
            "affectedChanges": len(unmappable),
            "detail": "Lexical proposals replace grammarCards with merged phrase boundaries; later grammar/translation changes target draft-array indexes that no longer identify a unique final token.",
            "resolution": "Apply lexical card arrays first, then regenerate or manually rebase grammar/translation changes by final phrase token plus occurrence. Do not apply draft indexes directly."
        })
    if repeated_conflicts:
        conflicts.append({
            "severity": "medium",
            "type": "repeated-line-consistency",
            "detail": repeated_conflicts,
            "resolution": "Use l020/l056 as the canonical merged-card bundle for l040, and choose one explicit Chinese translation for l037/l053 before merge."
        })
    if protected_touch:
        conflicts.append({"severity": "high", "type": "protected-mv-caption-touched", "detail": protected_touch,
                          "resolution": "Do not merge protected user-supplied content without a new explicit user instruction."})

    source_proposals = [
        {"role": role, "file": f"project/proposals/{role}.json", "changes": len(proposals[role]["changes"]),
         "scope": len(proposals[role].get("scope", {}).get("frameIds", [])), "sha256": sha256(PROPOSALS[role])}
        for role in ("lexical", "grammar", "translation")
    ]
    report = {
        "schemaVersion": 2,
        "reviewRole": "integration",
        "status": "completed",
        "baseFrameSha256": base_sha,
        "sourceProposals": source_proposals,
        "audit": {
            "protectedFrames": protected,
            "protectedFramesTouched": protected_touch,
            "proposalContractIssues": contract_issues,
            "lexicalArrayReplacements": len(lexical_arrays),
            "grammarCardChanges": len(grammar_card_changes),
            "translationCardChanges": len(translation_card_changes),
            "unmappableDraftIndexChanges": len(unmappable),
            "repeatedJapaneseGroups": [ids for ids in repeated.values() if len(ids) > 1]
        },
        "integrationPolicy": {
            "lexical": "Lexical token boundaries, readings, romaji and loanword annotations are the first-stage proposal.",
            "grammar": "Apply grammarStructureZh/functionZh only after phrase-boundary rebasing; grammar is canonical for grammar semantics.",
            "translation": "Apply caption.translationZh independently. Rebase zhMeaning/functionZh only to a unique final phrase token plus occurrence.",
            "protected": "mv-p001 and mv-p002 are user-supplied and are excluded from all automated changes.",
            "rawCaption": "Do not alter frozen QRC Japanese display text or timing."
        },
        "conflicts": conflicts,
        "recommendedProposalSet": {
            "lexical": {"file": "project/proposals/lexical.json", "accept": ["caption.furigana", "caption.romaji", "grammarCards phrase grouping", "loanword source"], "conditions": ["Do not overwrite protected MV captions.", "Use l020/l056 grouping for repeated l040."]},
            "grammar": {"file": "project/proposals/grammar.json", "accept": ["grammarStructureZh", "functionZh"], "conditions": ["Rebase after lexical grouping; do not apply draft indexes directly."]},
            "translation": {"file": "project/proposals/translation.json", "accept": ["caption.translationZh", "zhMeaning", "functionZh"], "conditions": ["Rebase after lexical grouping.", "Resolve l037/l053 differing full-line Chinese before merge."]}
        },
        "recommendation": "Proposal-only pass complete. Rebase all 94 structurally displaced card-field changes, normalize the two repeated-line inconsistencies, then present the consolidated review for explicit user approval; do not edit frames.json in this pass."
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "conflicts": len(conflicts), "unmappable": len(unmappable), "contractIssues": len(contract_issues), "protectedTouched": len(protected_touch)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
