# 5. Render, verify and deliver

Read active manifests, frames, review decision, selected renderer, timing and template snapshots, plus [06-layers.md](06-layers.md), [08-validation.md](08-validation.md) and [10-foreground-options.md](10-foreground-options.md).

## Prepare the active render

Verify accepted content and render authorization from the conversation or recorded evidence. Reuse an existing valid authorization. If the user has already requested the current correction and rerender, refresh stale hashes within that scope rather than asking the same question again. Do not run layer configuration or normalization simply to resume a render.

Rehearse the merge before the user approves rather than after: `python SKILL_ROOT/scripts/rehearse_merge.py PROJECT_ROOT` copies the JSON evidence into a scratch directory, runs the merge and the derived-artifact refresh against the copy, asserts the generic invariants and proves the real files were byte-identical. It reports `stale-accepted-set` (not a failure) when the change set was already applied.

After an accepted merge, `python SKILL_ROOT/scripts/apply_review_merge.py --project-root PROJECT_ROOT --accepted FILE --user-wording "VERBATIM" --source FILE ...` writes `merge-log.json` and `review-decision.json`, and `python SKILL_ROOT/scripts/refresh_after_merge.py --project-root PROJECT_ROOT` regenerates the review Markdown, rebuilds `particle-functions.json` from the cards actually in use and refreshes the draft manifest.

Write `project/render/render-plan.json` with `python SKILL_ROOT/scripts/write_render_plan.py PROJECT_ROOT --run-id ID [--renderer FILE] [--authorization-text TEXT]`: the run id, renderer hash, enabled features, audio policy, candidate path, the hashes the authorization will bind and the QA list implied by the enabled features. Verify that the selected renderer implements every enabled feature; a flag in JSON alone is not proof of implementation.

Optionally catch layout and graph problems before the authorized run with `python SKILL_ROOT/scripts/preflight_render.py PROJECT_ROOT`: it paints every unique foreground state (any unlayoutable card fails here) and encodes a short probe with the real filter chain, spectrum and codec-copied audio. No candidate is produced and the gate is not exercised.

The preflight wipes and recreates `project/work/preflight` on every run and leaves its state PNGs there as evidence. On a host that counts deletions per turn, the *second* run can be refused at that startup purge before a single state is painted: the report is then never refreshed and the script exits non-zero although nothing is wrong with the project - the stale report looks like a passing preflight for content it no longer describes. Move the previous scratch directory aside first (a rename, not a delete) so the purge has nothing to remove, and re-read `result`, `statesPainted`, `layoutFailures` and the `timeline` path in `project/qa/render-preflight.json` afterwards instead of trusting the exit code. A non-zero exit that happens *after* the report was written means only the trailing cleanup was refused; the report is still valid. Note that the preflight is not part of the render gate - `authorization_hash_paths` does not include it - so a stale report never blocks a render, which is exactly why it has to be checked by hand.

Select RENDERER_FILE before preparing commands: on resume use the recorded entryPoint (legacy renderer), including fixed-preset local extensions; for a new supported preset use the bundled renderer; custom timelines use a documented local entrypoint. Resolve its snapshotted timeline and helper closure. Run `python SKILL_ROOT/scripts/authorize_render.py PROJECT_ROOT --authorization-text "VERBATIM USER WORDING" --renderer RENDERER_FILE` when creating or rebinding authorization. Both use the common verify_render_gate.py with the actual entrypoint. The gate binds evidence, not substitute approval. See [11-portability.md](11-portability.md).

For a looping background, record what each seam looks like in the foreground with `python SKILL_ROOT/scripts/check_loop_seam.py PROJECT_ROOT`: it lists the seam times, the state at each one and whether a seam falls inside a lyric line, plus a contact sheet.

## Render candidates

1. Normalize text only for matching (NFKC, casefold, whitespace removal); keep original display text. Store `full`, `adjacentRows`, `japaneseFallback`, `lineFallback` or `unmatched`. Only `full`/`adjacentRows` supports word highlighting; unreliable matches fall back visibly rather than shifting later English.
2. Run the selected renderer's snapshotted timeline helper with PROJECT_ROOT, OUTPUT and --duration-ms N (bundled projects use SKILL_ROOT/scripts/build_foreground_timeline.py). Inspect display/countdown timing. Render each state on a fresh transparent canvas. Use static neighboring lines when enabled, not scrolling replacements.
3. Run `python RENDERER_FILE PROJECT_ROOT --run-id ID --canvas NAME` once per declared canvas. Project renderers compose the same contracts and call the common gate. Use background → foreground → optional transparent spectrum, CFR 30 unless explicitly configured otherwise. Use a fresh run ID after input/dependency changes; reuse caches only when all hashes match.
4. Preserve requested audio by codec copy and select a compatible container. FLAC uses MKV, not a renamed MP4. Probe stream start times and timestamp continuity; preserve master silence and avoid technically empty opening timestamps.

## QA and promotion

Run `python SKILL_ROOT/scripts/collect_qa.py PROJECT_ROOT CANDIDATE QA_DIR`. It also writes `contact-sheet.png`: one labelled grid of every sample. Inspect the sheet first and open an individual frame only where something looks wrong - it carries the same evidence at a fraction of the reading cost. Add samples for enabled features not automatically covered, particularly prelude, 3/2/1, first sung token, neighbor boundaries, long gaps and tail. Record concrete visual findings before marking the QA report `passed`.

Record those findings and flip the report in one verified step:

```text
python SKILL_ROOT/scripts/finalize_qa.py PROJECT_ROOT QA_REPORT --findings FINDINGS.md \
    --supplementary audio=project/qa/audio-preservation-candidate.json
```

It refuses to pass an unreviewed report, and refuses a report that no longer hashes the candidate on disk. Prove the audio was copied rather than re-encoded with `python SKILL_ROOT/scripts/verify_audio_copy.py PROJECT_ROOT CANDIDATE [--seconds N]`; the optional short probe fits the pre-render stage, the default compares the whole programme. Assert the compiled timeline with `python SKILL_ROOT/scripts/check_timeline_invariants.py PROJECT_ROOT TIMELINE_JSON` (contiguity, coverage, countdown at the first sung unit, prelude mode, gap/tail, state count) instead of re-checking those by hand.

Run `python SKILL_ROOT/scripts/validate_project.py PROJECT_ROOT --stage render --renderer RENDERER_FILE`. This verifies standard-schema structure and the selected renderer gate, not renderer behavior. For features outside its schema, record separate timeline/layer checks from reference 8. Never claim a structural validator verifies visual behavior.


After passing QA, run `python SKILL_ROOT/scripts/promote_final.py PROJECT_ROOT CANDIDATE QA_REPORT`. It verifies the candidate hash before copying and updating final state/manifest. Open or link the actual promoted files and report key changes and any remaining limitation. Keep candidates/debug assets outside `deliverables/final/`.
