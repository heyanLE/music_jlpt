---
name: japanese-song-study-video
description: Create, review, and render Japanese song-learning videos from music, cover art, timed lyrics, and optional footage. Includes word cards, kanji readings, romaji, static neighboring lyrics, an opening countdown, spectrum overlays, and platform covers.
---

# Japanese Song Study Video

Produce video files using the snapshotted series template. Use five stages, and resume existing projects from verified files rather than recreating work from conversation memory.

## Start or resume

1. Set `SKILL_ROOT` to the directory containing this file and `PROJECT_ROOT` to the explicitly selected `projects/<slug>` directory. Use absolute script and project paths; do not assume the shell's working directory. In commands below, replace these placeholders with those absolute paths. Locate working Python, FFmpeg and ffprobe executables in the current environment; do not copy another project's runtime paths.
2. For an existing project run `python SKILL_ROOT/scripts/inspect_project.py PROJECT_ROOT`. Read its findings, `project/build-state.json`, active manifests, review decision, and render authorization. A state label alone is not evidence of completion: check files and hashes reported by the inspector.
3. Read only the current stage and its linked references. Repair missing or stale artifacts at the earliest affected stage. Preserve frozen sources, human edits, accepted proposals, and completed outputs. Record selected paths, completed evidence, current issue, next action, and relevant user wording in `project/build-state.json` so another context can continue.

| Stage | Read when needed | Completion evidence |
| --- | --- | --- |
| 1. Inputs | [01-inputs.md](references/01-inputs.md) | frozen sources, explicit layer and timing configuration; `inputs_confirmed` |
| 2. Preparation | [02-project-setup.md](references/02-project-setup.md) | decoded timing, palette, template snapshots, layout/structure checks; `setup_complete` |
| 3. Draft cards | [03-card-draft.md](references/03-card-draft.md), [12-lexicon-rag.md](references/12-lexicon-rag.md) | all lines/cards, editable review Markdown, layout report; `draft_ready` |
| 4. Intelligent review | [04-assisted-review.md](references/04-assisted-review.md) | lexicon reuse + one targeted online review of unresolved spans (new projects), or the legacy three-role proposals + integration (existing projects); accepted merge and content decision; `review_approved` |
| 5. Video | [05-render.md](references/05-render.md) | authorized candidate, visual/technical QA, promoted final; `qa_passed` then `delivered` |

Card drafting reuses the workspace lexicon before authoring anything new: match each lyric row longest-first against `lexicon/lexicon.json`, keep the matches the lexicon can vouch for, and send only the unmatched or low-confidence spans to review. Reliability is per entry and moves with the user's accept/reject decisions, so reuse improves project over project. See [12-lexicon-rag.md](references/12-lexicon-rag.md).

Cover-only work uses [07-covers.md](references/07-covers.md) after preparation. It does not require redoing lyric review.

For clone/device migration or repository packaging, first use [11-portability.md](references/11-portability.md). Inspection alone is read-only: do not rewrite plans, approvals or state merely to report readiness. A current request not to render overrides historical render authorization.

Renderer selection is independent of background preset. On resume use the recorded project renderer (plan `entryPoint` or legacy `renderer`), including documented fixed-preset extensions. Do not replace it with the global renderer solely because the preset is fixed. Bind local dependencies as described in reference 11.

## Configuration and authority

- `source/` and its manifest preserve original input evidence. `project/timing/` preserves decoded source timing.
- `project/frames.json` is the sole active linguistic/render-content source. Review Markdown is an editable human input, not a parallel renderer input: import its field changes with a diff before any regeneration.
- `project/input-manifest.json` owns media, outputs and signed alignment; `scene-timeline.json` owns background scheduling; `presentation.json` owns foreground and spectrum options.
- `project/templates/` contains active template snapshots; `palette.json` owns project colors. Resolved layout and preview images are derived evidence, not competing configuration. Do not borrow a historical renderer or replace snapshots with a newer global template silently.
- `project/review/` records role evidence, merges and decisions. `project/render/` records the selected renderer and plan; `project/qa/` contains validation evidence. Work products stay in `project/work/<runId>/`; final deliverables are promoted to `deliverables/final/`.

New projects default to the learning-assistance input `--learning-assist on`: static previous/next lyrics and a 3-second opening countdown. Prelude foreground separately defaults to `first-line`. These are independent of background preset and spectrum. Fields, exact behavior and old-project migration are defined only in [10-foreground-options.md](references/10-foreground-options.md).

The three layers are background → foreground (veil + study content) → optional transparent spectrum. Read [06-layers.md](references/06-layers.md) for rendering and [09-presets-alignment.md](references/09-presets-alignment.md) for presets/timing.

## Decisions and continuation

Review proposals and final rendering require user authorization for their scope, but do not ask again for authorization already given in the conversation or recorded with its wording. `继续` advances current authorized work; alone it does not newly accept proposals or authorize an otherwise unapproved final render. A request explicitly including both acceptance and rendering can satisfy both decisions.

Shared tooling lives in this skill's `scripts/`. Use it instead of writing a project-local copy: a private duplicate is how the same bug was fixed in four places. Project-local scripts remain valid only for genuinely project-specific renderers or custom scene timelines, and only when the bundled script cannot express the need - say why in the project's build-state. Rehearsals, previews and QA helpers are always the shared ones.

Input/content/style/renderer changes invalidate affected hashes and downstream evidence. Refresh that evidence and rebind render authorization for changes the user already requested; a hash change by itself is not a new permission question. Only unresolved linguistic proposals or a materially new choice outside the authorized scope need a new decision. Never fabricate approval text or label machine-generated content human-confirmed.

## Essential output properties

Keep original Japanese/English display order and trustworthy timing. Kanji-only hiragana, confirmed loanword sources and token romaji share lyric anchors; English has highlighting but no ruby, romaji or grammar cards. Cards occupy one horizontal row and never highlight; the token stays on one line while the meaning/function and the grammar structure may each use two. See stages 3 and 5 for checks.

Use UTF-8 JSON without BOM. Preserve requested audio without lossy re-encoding; FLAC stream copy uses MKV. Do not claim lossless source quality for an MP3. Never promote an unchecked candidate or claim success from a state label or an unverified link.

Deliver the episode description with the video: generate it from the frozen build with `scripts/write_video_description.py` (see `references/13-video-description.md`) instead of retyping it, so the title, work, artist and the real audio format cannot drift from the finished file.
