# Music JLPT workspace

For song-learning video work, read `.agent/skills/japanese-song-study-video/SKILL.md` completely, then only the relevant stage references. This checked-in skill is the workspace authority; do not silently use a same-named personal skill or a newer template.

The full skill deliberately lives in the user-requested `.agent` directory. Codex's automatic repository skill location is `.agents/skills`; this AGENTS.md supplies an explicit entrypoint without a second divergent copy. If the application does not discover it automatically, open the above SKILL.md directly.

Select the requested `projects/<slug>` explicitly. On a different device read `TRANSFER.md` and the skill's portability reference before resuming. Do not initialize over an existing project, re-import edited lyrics, reset approved review, or rerender merely because the conversation history is unavailable.

Before the first render on a new machine, context or clone, run the environment doctor:

```sh
python -B .agent/skills/japanese-song-study-video/scripts/bootstrap_env.py
```

It reports where Python, FFmpeg, Node and the CJK font are, installs the pinned Python dependencies when they are missing, and exits non-zero while anything required is absent. A gitignored local runtime report may be kept as `runtime.local.json`.

Keep media private. Source audio/video/artwork and final outputs use Git LFS. No secrets, machine dependency folders or regenerated state PNG caches belong in a commit. Preserve exact JSON/script bytes because audits use SHA256. A successful Git push is not evidence that LFS media was uploaded: verify LFS and remote refs.
