# 5. Render, verify and deliver

Read active manifests, frames, review decision, selected renderer, timing and template snapshots, plus [06-layers.md](06-layers.md), [08-validation.md](08-validation.md) and [10-foreground-options.md](10-foreground-options.md).

## Prepare the active render

Verify accepted content and render authorization from the conversation or recorded evidence. Reuse an existing valid authorization. If the user has already requested the current correction and rerender, refresh stale hashes within that scope rather than asking the same question again. Do not run layer configuration or normalization simply to resume a render.

Write `project/render/render-plan.json` with the run ID, active source/config/content/template/renderer hashes, canvases, signed alignment, selected audio codec/container, feature settings and candidate path. Verify that the selected renderer implements every enabled feature; a flag in JSON alone is not proof of implementation.

Select RENDERER_FILE before preparing commands: on resume use the recorded entryPoint (legacy renderer), including fixed-preset local extensions; for a new supported preset use the bundled renderer; custom timelines use a documented local entrypoint. Resolve its snapshotted timeline and helper closure. Run `python SKILL_ROOT/scripts/authorize_render.py PROJECT_ROOT --authorization-text "VERBATIM USER WORDING" --renderer RENDERER_FILE` when creating or rebinding authorization. Both use the common verify_render_gate.py with the actual entrypoint. The gate binds evidence, not substitute approval. See [11-portability.md](11-portability.md).

## Render candidates

1. Normalize text only for matching (NFKC, casefold, whitespace removal); keep original display text. Store `full`, `adjacentRows`, `japaneseFallback`, `lineFallback` or `unmatched`. Only `full`/`adjacentRows` supports word highlighting; unreliable matches fall back visibly rather than shifting later English.
2. Run the selected renderer's snapshotted timeline helper with PROJECT_ROOT, OUTPUT and --duration-ms N (bundled projects use SKILL_ROOT/scripts/build_foreground_timeline.py). Inspect display/countdown timing. Render each state on a fresh transparent canvas. Use static neighboring lines when enabled, not scrolling replacements.
3. Run `python RENDERER_FILE PROJECT_ROOT --run-id ID --canvas NAME` once per declared canvas. Project renderers compose the same contracts and call the common gate. Use background → foreground → optional transparent spectrum, CFR 30 unless explicitly configured otherwise. Use a fresh run ID after input/dependency changes; reuse caches only when all hashes match.
4. Preserve requested audio by codec copy and select a compatible container. FLAC uses MKV, not a renamed MP4. Probe stream start times and timestamp continuity; preserve master silence and avoid technically empty opening timestamps.

## QA and promotion

Run `python SKILL_ROOT/scripts/collect_qa.py PROJECT_ROOT CANDIDATE QA_DIR`. Inspect generated screenshots and add samples for enabled features not automatically covered, particularly prelude, 3/2/1, first sung token, neighbor boundaries, long gaps and tail. Record concrete visual findings before marking the QA report `passed`.

Run `python SKILL_ROOT/scripts/validate_project.py PROJECT_ROOT --stage render --renderer RENDERER_FILE`. This verifies standard-schema structure and the selected renderer gate, not renderer behavior. For features outside its schema, record separate timeline/layer checks from reference 8. Never claim a structural validator verifies visual behavior.


After passing QA, run `python SKILL_ROOT/scripts/promote_final.py PROJECT_ROOT CANDIDATE QA_REPORT`. It verifies the candidate hash before copying and updating final state/manifest. Open or link the actual promoted files and report key changes and any remaining limitation. Keep candidates/debug assets outside `deliverables/final/`.
