# Layer, layout and timing contract

Read for presentation configuration, timeline compilation, rendering or QA. Foreground visibility, neighbors and countdown are defined in [10-foreground-options.md](10-foreground-options.md); do not redefine them in project notes.

## Composition

Exactly three layers, in this order:

1. `background`: video/still assets, fit and background fades.
2. `foreground`: one unified veil, normal top-center cover, study text and grammar cards.
3. `floatingOverlay`: optional transparent Foobar spectrum.

A background transition affects only its layer unless an explicitly requested custom timeline sets `scope: all-layers`. Fixed presets use `background-only`. Do not add independent black blocks behind lyrics or cards; the unified veil follows configured foreground visibility.

## Background

`project/scene-timeline.json` is the sole schedule, using final-output time from zero to output end:

- `video-loop`: muted video loops; preserve aspect ratio, scale to canvas height and center horizontally.
- `video-clip`: play the selected source range once, with the same fit and muted source audio.
- `cover-gaussian`: crop the cover for the background only, blur and shade using the snapshot.
- `still-cover` / `solid`: explicit custom modes.

Record fit/pillarbox or crop decisions explicitly. Never stretch footage. Scene `foregroundMode` overrides presentation's default for that scene; transition scope and duration are shared at each adjacent boundary.

## Foreground geometry and colors

Use `project/templates/foreground.json`, snapshotted from `study-current-v3`, with its resolved layout. The order is cover → annotation → original lyric → romaji → optional sentence Chinese → one card row. Verify the renderer reproduces the snapshot; a matching template ID alone does not verify geometry.

Japanese tokens, annotations and romaji share measured anchors. Draw explicit `caption.furigana` spans only over kanji, left-aligned to the run. Do not reconstruct ruby from card readings or duplicate literal kana. Center a confirmed `sourceWord` above its katakana token. English retains original position/highlighting and no annotation, romaji or cards. Current-token annotation and romaji highlight with that token. Cards never highlight.

Use the verified bold font, black text outlines, palette-derived active color and semi-transparent palette-colored cards. Check highlight visibility against the veil. Cards have three fields: token → meaning/function → `grammarStructureZh` (legacy `posZh` only when absent). Meanings wrap at fixed font size to at most two lines; the other fields stay one line. An overflow is a concrete field/layout issue, not permission to wrap the card row or insert colons/separators.

## Spectrum and audio

Use the fixed `spectrum-foobar-bars` overlay and `python SKILL_ROOT/scripts/render_foobar_spectrum.py AUDIO PALETTE OUTPUT --duration-ms N --offset-ms N`. It has an RGBA canvas, no black background, occupies the bottom, and responds to aligned audio through the complete output. It is unaffected by foreground gaps and background-only transitions. When disabled, omit its input.

`alignment.offsetMs` assigns music time zero to the output clock: positive delays music/lyrics/spectrum; negative trims/shifts them earlier. Do not apply it to background timestamps. Preserve raw source timing and apply the offset exactly once. Details and constraints: [09-presets-alignment.md](09-presets-alignment.md).
