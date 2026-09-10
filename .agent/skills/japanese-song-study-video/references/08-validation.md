# Validation and recovery checks

Mechanical validators complement visual inspection. Check the selected stage and the changed dependencies; do not repeatedly run unrelated work after evidence passes.

## Setup

- Frozen source paths/hashes match manifests; decoded tracks have expected language, row count and timing units.
- Scene schedule, alignment and spectrum choices are explicit.
- Learning assistance and prelude inputs are written; old-project migration is recorded.
- JSON parses as UTF-8 without BOM; template/palette/layout agree.
- Bold CJK text and shared anchors render correctly; cover and palette match the project.

## Draft and review

- Every real lyric row, including English, has a frame.
- Sentence Chinese preserves matched QMTS or human provenance.
- Kanji spans have contextually reviewed hiragana; literal kana is not redundantly annotated.
- Confirmed loanwords have source-word annotations; English has none.
- Cards have exactly one meaning/function field and a grammar field, no label-colons, no clipped text and one horizontal row.
- Human Markdown edits were imported before regeneration; accepted fields and repeated-line translations were preserved.
- Role proposals, integration, seal, merge and decision hashes agree with their respective input/output frame versions.

## Render and visual evidence

- The common render gate passes for the actual fixed or custom renderer.
- Output stream duration, resolution, CFR rate, audio codec, start times and continuity pass probing.
- Music, lyrics and spectrum share one signed offset; background source audio is muted unless explicitly part of a custom audio sequence.
- Layer order, unified veil, cover position, magic color, transparency and bold outlines match the active template.
- Enabled learning assistance is visible: correct previous/next content at actual video edges, no slide animation, first-line prelude when selected, 3/2/1 timed to the first sung unit without added music delay.
- Disabled learning features produce no remnants. Scene gap/tail behavior follows reference 10.
- Current lyric, ruby and romaji highlight correctly; pure/mixed English remains aligned; cards never highlight.
- Spectrum is transparent and moves through beginning/middle/end; fades and scene boundaries do not reset it.
- Inspect first/last lyric, longest card, repeated line, split timing, English, gaps, all transitions and feature-specific samples.

Run `python SKILL_ROOT/scripts/validate_project.py PROJECT_ROOT --stage setup|draft|render` at applicable boundaries, using a single concrete stage value. For render stage pass `--renderer RENDERER_FILE`. Standard-schema validation and the gate do not prove custom renderer behavior; record custom checks separately.

On failure, record the issue in `project/qa/`, preserve the candidate, set `render_failed` or `qa_failed`, and repair only the affected dependencies. Promotion requires the current candidate hash and a visually passed QA report.
