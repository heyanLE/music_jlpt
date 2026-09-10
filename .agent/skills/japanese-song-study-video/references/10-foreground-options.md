# Foreground input: learning assistance and visibility

This is the single behavior contract for new-project defaults, existing-project migration, neighboring lyrics, opening countdown and foreground visibility. Background presets do not redefine these rules.

## Inputs and precedence

On first configuration when no `presentation.json` exists, `configure_layers.py` defaults to `--learning-assist on`. This combined input enables both previous/next lyrics and the opening countdown. `--learning-assist off` disables both. Individual `--neighbors on|off` and `--countdown on|off` override the combined switch for their feature, regardless of argument order.

`--prelude-mode first-line|hidden` is independent and defaults to `first-line` for new projects. Turning learning assistance off does not hide prelude content; use the prelude option for that.

Write the resolved values under `project/presentation.json`; do not add a second boolean `learningAssist` that could conflict with them. This is a valid fragment to merge into the existing foreground object, not a replacement for the entire file:

```json
{
  "foreground": {
    "neighbors": { "enabled": true },
    "countdown": { "enabled": true, "durationMs": 3000 },
    "preludeMode": "first-line"
  }
}
```

Only 3000 ms is currently supported: 3, 2, 1 for one second each. Neighbor gap/opacity and countdown badge geometry follow the fixed renderer/template; they are not additional user inputs.

## Previous and next lines

When `neighbors.enabled=true`, place the immediately previous lyric to the current lyric's left and the immediately next lyric to its right, on the **same lyric/annotation/romaji rows**. Current lyric remains centered. The neighboring text uses a lower opacity and the same measured annotation/token anchors. Clip only at the actual video edges, with no inset clipping boundary.

Show only neighboring lyric, its kanji/loanword annotations and Japanese romaji. Do not duplicate neighbor covers, translations, cards or veils. A missing previous/next line produces no placeholder and does not wrap from last to first. English retains source position and no extra annotation or romaji.

Switch the current and neighboring rows using the existing line-switch timing. There is no sliding, downward motion, scroll, or newly introduced transition duration. Only the current line follows its original highlighting; neighbors stay inactive. Disabling neighbors restores current-line-only geometry.

## Opening countdown

The software selects the first nonempty normalized lyric row; it does not recognize singing from audio. Setup/draft must first exclude verified credits/metadata and separate spoken introductions from learning lyrics. Check uncertain first-singing timing against the audio before accepting it. Use the selected row’s first nonempty QRC part start; if word parts are absent, use the lyric row start (e.g. LRC). Apply the project’s signed lyric offset exactly once to obtain output time `T`.

- 3: `[T − 3000, T − 2000)`
- 2: `[T − 2000, T − 1000)`
- 1: `[T − 1000, T)`

Display the small palette-colored countdown badge at the template's upper-right position, clear of cover/text. It disappears at `T`; there is no 0 or repeated countdown at interludes. If a range begins before output time zero or ends after output end, show only the visible portion. If the whole countdown is before output start, show none. Record clipped intervals in the timeline report.

The countdown does not insert silence, trim master silence, shift music, or change lyric/scene/spectrum timestamps. It can display even when `preludeMode=hidden`; the badge and study foreground have separate visibility decisions.

## Prelude, lyric gaps and tail

Before the first lyric:
- `preludeMode=first-line`: show the complete first study frame, unhighlighted, including cover, annotations, romaji, translation when enabled, and cards. Neighbors follow their own switch.
- `preludeMode=hidden`: no learning foreground. Preserve a previously explicit scene `idleForeground: "cover"` override if present; it shows only the normal cover, not a veil or learning content.

After the first lyric starts, scene `foregroundMode` overrides presentation `defaultMode`:
- `follow-lyrics`: hold within internal QRC/respiration gaps. After a line ends, retain it for up to `tailProtectionMs=500` ms (currently fixed; other values are unsupported), stopping earlier at the next line, then hide until the next line.
- `persistent`: retain the current line through interludes until the next starts; retain the last line to output end.

On a follow→persistent boundary, immediately restore the latest lyric even if its follow-mode protection expired. Prelude mode remains the authority if the boundary is still before the first lyric. All displayed complete study states use one unified foreground veil; spectrum persistence is independent.

## Existing projects and migration

Missing legacy fields mean neighbors off, countdown off and prelude hidden. Merely reading, inspecting or rerendering an existing project must not opt it into new defaults. Preserve explicitly stored values when a new argument is omitted.

For a requested migration, use:

```text
python SKILL_ROOT/scripts/update_learning_aids.py PROJECT_ROOT --learning-assist on
```

This enables the two learning aids while preserving the existing prelude mode (legacy missing means hidden). Add `--prelude-mode first-line` only when the requested migration also includes showing the first study frame throughout the prelude.

This targeted helper preserves scene timing, offsets, palette, styling, templates and reviewed content. Do not use full `configure_layers.py` for a feature-only migration. Record previous/resolved options and the user's request in project state/render notes; refresh layout/timeline QA and render authorization hashes within the already authorized scope. For project-local renderers, verify actual support or adapt them before claiming the option works.

## Required samples

Check prelude, all visible 3/2/1 values, first sung part, a middle line with both neighbors, first/last line boundaries, an interlude and tail. Verify enabled/disabled behavior, correct timing without audio movement, shared ruby/romaji anchors, no neighbor highlighting, no hidden clipping margin and no new animation.
