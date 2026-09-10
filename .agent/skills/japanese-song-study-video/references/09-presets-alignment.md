# Background presets and audio alignment

Preset selection configures visual scheduling; it never supplies linguistic approval or replaces stage 4. Learning assistance is an independent input defined in [10-foreground-options.md](10-foreground-options.md).

## Named presets

Configure using `python SKILL_ROOT/scripts/configure_layers.py PROJECT_ROOT --preset PRESET --spectrum on|off ...`.

| Preset ID | Background | Foreground after first lyric |
| --- | --- | --- |
| `video-loop-follow` | Muted source video loops for output duration | `follow-lyrics` |
| `video-then-gaussian-hybrid` | Video once, then blurred cover | `follow-lyrics` during video; `persistent` during Gaussian |
| `gaussian-persistent` | Blurred cover throughout | `persistent` |

For hybrid, default transition is background-only black fade out/in lasting 500 ms. `transitionAtMs=auto` uses the probed video duration. A shorter transition trims the video; a longer one requires explicit `--stage1-loop`. Height-centered video preserves aspect ratio.

`custom` uses an explicit scene/presentation description and a project-local renderer. Resolve requested multi-video order, duration, looping, source ranges, fades, fit, foreground modes and spectrum; derive routine values from the request and probes and record them. Ask only if a missing choice materially changes the result. Never substitute a single-video preset for a multi-video schedule. Custom rendering must call the common render gate and implement the selected foreground contract.

Spectrum defaults off unless requested. When enabled, it uses the fixed Foobar overlay above the foreground.

## Signed alignment

- `none`: `offsetMs=0`.
- `manual`: record the signed `--offset-ms` and user request or verified reason.
- `onset`: run `python SKILL_ROOT/scripts/detect_audio_offset.py MUSIC BACKGROUND REPORT`. The proposed offset is background onset minus music onset.

Detection is evidence, not an automatically applied offset. Inspect confidence and the actual audio relationship; when the user requested offset matching, apply a supported result within that authorization using `configure_layers.py --offset-mode onset --offset-report REPORT`. If confidence is low or the clips contain unrelated dialogue/arrangements, investigate another matching segment; do not silently use a guess. Ask only if the remaining uncertainty requires a user choice.

Apply the same offset once to music, lyrics and spectrum, never the background. Countdown timing is derived after that offset. Do not shift audio solely to make room for a countdown. Preserve source/master silence. For codec-copy output, probe actual packet/stream starts, negative trimming boundaries and player-compatible timestamp continuity; do not assume a container gap is equivalent to encoded silence.
