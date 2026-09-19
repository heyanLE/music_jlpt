# 1. Determine and freeze inputs

Read [09-presets-alignment.md](09-presets-alignment.md) for scene selection and [10-foreground-options.md](10-foreground-options.md) for the learning-assistance input.

## Resolve the request

Map each supplied file to its user-declared role. Use attachment order when the user explicitly assigns it; otherwise resolve from names/probes and ask only about a remaining material ambiguity.

| Input | Rule |
| --- | --- |
| Music | Exactly one source; a video source is allowed and its audio is extracted by stream copy. Preserve original audio quality. |
| Foreground cover | Explicit artwork takes precedence; otherwise extract the music's embedded cover. If absent, request or use an explicitly authorized alternative. |
| Lyrics | LRC, or QQ `qm` with supplied `qmRoma` and `qmts` companions. Record absent companions; do not claim readings/translations came from a file that was not supplied. |
| Background | Named video/Gaussian/hybrid preset, or a complete custom schedule. Multiple videos with looping/order/fades use an explicit custom timeline. |
| Spectrum | User choice; default off. |
| Learning assistance | Combined previous/next lyrics + opening countdown; default on for new projects. Individual overrides and prelude behavior are in reference 10. |
| Veil | Black, opacity 0.28 by default, within the foreground. Respect explicit scene/user overrides. |
| Alignment | Signed music-to-output offset; default `none`/0. Detect requested uncertain offsets before fixing the active timeline. |
| Output | Default 1920×1080 CFR 30; record all requested canvases. |

Resolve the background from the user's stated intent; routine geometry or transition defaults do not require a separate question. Record assumptions. An unrelated historical project does not supply missing inputs.

When the music-to-background relationship is uncertain, `python SKILL_ROOT/scripts/diff_background_alignment.py MUSIC BACKGROUND REPORT` produces the evidence: per-window offset and score plus a summary saying whether one linear alignment is plausible. Read it as evidence only - `configure_layers.py --offset-mode onset|manual` is what applies an offset, and the reason is recorded with it. Two distinct offset clusters mean the video is an edit rather than a single excerpt of the song.

If the user later supplies different artwork, `python SKILL_ROOT/scripts/replace_cover.py PROJECT_ROOT NEW_IMAGE --reason TEXT` installs it as a new cover revision: the previous cover is archived inside `source/`, both revisions are recorded with hashes in `source/source-manifest.json` and a build-state note is appended. It does not re-export covers or regenerate previews; do that next, and remember that any existing render authorization becomes stale.

## Create the configuration

For a new project run `python SKILL_ROOT/scripts/freeze_inputs.py PROJECT_ROOT --help`, then invoke it with the resolved assets. It creates role-named frozen copies and probes, extracts embedded artwork and music-video audio, and writes `source/source-manifest.json`. Do not rerun initialization over an existing reviewed project.

Run `python SKILL_ROOT/scripts/configure_layers.py PROJECT_ROOT --help` and configure the selected preset or custom files. Supply `--spectrum on|off`; new projects may use `--learning-assist on` explicitly to make the default visible. Inspect the written files:

- `input-manifest.json`: source paths, codec preservation, output canvases, and signed alignment.
- `scene-timeline.json`: background schedule on final-output time.
- `presentation.json`: foreground and spectrum configuration.

Set `inputs_confirmed` after every active source is frozen/probed and the schedule is complete. Record unresolved inputs instead of inventing media, timing, translations, or user decisions. Later changes invalidate only the dependent setup/review/render evidence.

## Freeze what a later edit would otherwise re-open

Two decisions cost real rework when they are taken late, so settle them here, once, and record them in `build-state.json`:

- **Cover copy and artwork together**: title, artist, subtitle, badge and the artwork revision. A subtitle edit after the video is rendered is harmless, but three successive artwork/palette revisions force every preview, gallery, layout check and pre-flight to be regenerated each time.
- **Whether the palette follows the artwork.** `palette.json` drives the card fill and highlight colour *inside the video* as well as the cover accents. Re-deriving it is a video-affecting change, so it is a separate decision from swapping the cover image: record "palette follows artwork" or "palette pinned" explicitly rather than letting a re-derive happen by accident.

## Keep export-only settings out of the manifest

`input-manifest.json` is hashed into the render authorization, so anything stored there becomes a video-input by definition. Cover copy, badge choices and export dimensions do **not** affect a single rendered frame: keep them in `project/render/cover-content.json` (see [07-covers.md](07-covers.md)) and leave the manifest to media, outputs and alignment. Otherwise editing a subtitle invalidates the render authorization for a video that did not change, and the gate correctly refuses the next render (`Render authorization hash missing or stale: inputManifestSha256`).
