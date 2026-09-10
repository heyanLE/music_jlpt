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

## Create the configuration

For a new project run `python SKILL_ROOT/scripts/freeze_inputs.py PROJECT_ROOT --help`, then invoke it with the resolved assets. It creates role-named frozen copies and probes, extracts embedded artwork and music-video audio, and writes `source/source-manifest.json`. Do not rerun initialization over an existing reviewed project.

Run `python SKILL_ROOT/scripts/configure_layers.py PROJECT_ROOT --help` and configure the selected preset or custom files. Supply `--spectrum on|off`; new projects may use `--learning-assist on` explicitly to make the default visible. Inspect the written files:

- `input-manifest.json`: source paths, codec preservation, output canvases, and signed alignment.
- `scene-timeline.json`: background schedule on final-output time.
- `presentation.json`: foreground and spectrum configuration.

Set `inputs_confirmed` after every active source is frozen/probed and the schedule is complete. Record unresolved inputs instead of inventing media, timing, translations, or user decisions. Later changes invalidate only the dependent setup/review/render evidence.
