# 5. Render, verify and deliver

Read active manifests, frames, review decision, selected renderer, timing and template snapshots, plus [06-layers.md](06-layers.md), [08-validation.md](08-validation.md) and [10-foreground-options.md](10-foreground-options.md).

## Prepare the active render

Verify accepted content and render authorization from the conversation or recorded evidence. Reuse an existing valid authorization. If the user has already requested the current correction and rerender, refresh stale hashes within that scope rather than asking the same question again. Do not run layer configuration or normalization simply to resume a render.

Write `project/render/render-plan.json` with the run ID, active source/config/content/template/renderer hashes, canvases, signed alignment, selected audio codec/container, feature settings and candidate path. Verify that the selected renderer implements every enabled feature; a flag in JSON alone is not proof of implementation.

Run `python SKILL_ROOT/scripts/authorize_render.py PROJECT_ROOT --authorization-text "VERBATIM USER WORDING" --renderer RENDERER_FILE` when creating or rebinding authorization. Select the fixed renderer for a supported preset and the documented project-local renderer for custom timelines. Both must use `python SKILL_ROOT/scripts/verify_render_gate.py PROJECT_ROOT --renderer RENDERER_FILE` before creating render media. The gate binds current evidence, not a substitute approval invented by the agent.

## Render candidates

1. Normalize text only for matching (NFKC, casefold, whitespace removal); keep original display text. Store `full`, `adjacentRows`, `japaneseFallback`, `lineFallback` or `unmatched`. Only `full`/`adjacentRows` supports word highlighting; unreliable matches fall back visibly rather than shifting later English.
2. Run `python SKILL_ROOT/scripts/build_foreground_timeline.py PROJECT_ROOT OUTPUT --duration-ms N` and inspect its display/countdown timing. Render each state on a fresh transparent canvas. Use static neighboring lines, not a scrolling or sliding replacement.
3. For supported fixed presets run `python SKILL_ROOT/scripts/render_video.py PROJECT_ROOT --run-id ID --canvas NAME` once per declared canvas. Custom renderers compose the same contracts and call the common gate. Use background → foreground → optional transparent spectrum, CFR 30 unless explicitly configured otherwise.
4. Preserve requested audio by codec copy and select a compatible container. FLAC uses MKV, not a renamed MP4. Probe stream start times and timestamp continuity; preserve master silence and avoid technically empty opening timestamps.

## QA and promotion

Run `python SKILL_ROOT/scripts/collect_qa.py PROJECT_ROOT CANDIDATE QA_DIR`. Inspect generated screenshots and add samples for enabled features not automatically covered, particularly prelude, 3/2/1, first sung token, neighbor boundaries, long gaps and tail. Record concrete visual findings before marking the QA report `passed`.

Run `python SKILL_ROOT/scripts/validate_project.py PROJECT_ROOT --stage render --renderer RENDERER_FILE`. This verifies standard-schema structure and the selected renderer gate, not renderer behavior. For features outside its schema, record separate timeline/layer checks from reference 8. Never claim a structural validator verifies visual behavior.

For existing projects the recorded entrypoint takes precedence over the preset-based defaults above: a fixed preset may have a project-local extension. Invoke that entrypoint and preserve its helpers. Use a fresh run ID after any render-input/dependency change; reuse cached states only when the complete hash set matches. See [11-portability.md](11-portability.md).

After passing QA, run `python SKILL_ROOT/scripts/promote_final.py PROJECT_ROOT CANDIDATE QA_REPORT`. It verifies the candidate hash before copying and updating final state/manifest. Open or link the actual promoted files and report key changes and any remaining limitation. Keep candidates/debug assets outside `deliverables/final/`.
