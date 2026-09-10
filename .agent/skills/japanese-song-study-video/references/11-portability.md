# Clone, handoff and reproducibility

Use for another device/context, Git packaging or dependency changes. This is not a new production stage and never automatically triggers rendering.

## Read-only acceptance after clone

1. Identify this checked-in skill and the requested project. Inspect Git status and LFS hydration. A file beginning `version https://git-lfs.github.com/spec/v1` is a pointer, not usable media. Fetch only from the user's selected remote.
2. Read repository TRANSFER.md when present. Run `inspect_project.py PROJECT_ROOT --renderer RECORDED_ENTRYPOINT`. Resolve plan `entryPoint` first, legacy `renderer` second; otherwise consult notes, never infer the entrypoint from the preset.
3. Verify active source/final media hashes. Historical absolute input paths are provenance, not active assets needing rewriting. Missing caches/candidates do not invalidate a final whose own hash verifies. Do not regenerate reviewed frames to recover media.
4. Check Python >=3.10, Pillow/numpy, FFmpeg/ffprobe features and a verified bold CJK font. Node/npm are needed only for encrypted QRC import, not already decoded timing. Use PATH/current-machine configuration rather than old username paths. Use `scripts/check_runtime.py` for a read-only runtime inventory.
5. Preserve the approved font family/index and record its SHA256. `STUDY_FONT` can point to a font installed on the destination. A substitute font changes layout and requires preview QA, not silent fallback. Do not redistribute proprietary fonts or bundled third-party executables.
6. Report content approval, media completeness, dependency availability and final-output validity separately. Successful clone or inspector alone does not establish complete reproducibility.

Inspection does not mutate state. An authorized migration may snapshot dependencies and change path resolution; archive old entrypoint/authorization and mark downstream render evidence stale. Preserve content approval and do not rerender until requested. Current no-render instructions override old authorization.

## Transport policy

Keep source media/lyrics, active JSON/templates, all human review Markdown, sealed proposals/integration/merge/decisions, project scripts/helper closure, QA reports with representative screenshots, and requested finals. Do not blindly ignore project/work: older projects keep unique review/build scripts there. Retain those scripts/evidence; rebuild state PNG batches, waveform caches and dependency installations.

Use Git LFS for large media. Preserve raw bytes in .gitattributes because approval seals hash JSON/code. Verify Git refs AND LFS upload completion; do not bypass LFS upload checks. On quota failure stop and ask about storage, never purchase quota automatically. Check remote privacy and material scope before upload; exclude credentials and machine runtime folders. Disclose exclusions. A source-only clone is not a media backup.

## Project dependency contract

Snapshot helper files inside project/render when output depends on them. Record project/render/renderer-dependencies.json:

```json
{"schemaVersion":1,"files":["project/render/foreground_layout.py","project/render/runtime/build_foreground_timeline.py","project/render/runtime/foreground_options.py","project/render/runtime/verify_render_gate.py"]}
```

Paths are project-relative regular files. List every local imported/invoked helper, including the gate and enabled overlay. Authorization binds this manifest and each file. The gate cannot discover arbitrary Python dependencies: inspect imports/subprocess calls before claiming complete coverage. Machine-local font/runtime versions belong in the render report. Use a new run ID after dependencies change.
