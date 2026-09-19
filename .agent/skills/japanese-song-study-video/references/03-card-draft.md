# 3. Generate the reviewable card draft

Read frames, decoded timing and the active foreground snapshot. Import any existing human review edits before writing content.

## Content source

Use one frame per displayed lyric row, including pure English. Preserve raw Japanese-English order and QRC ranges. For full-line Chinese, first use the decoded `qmts` track and verify its row/time mapping; next prefer a supplied or human-reviewed translation. Generated translations are provisional and must retain that provenance.

Split Japanese into learning-value tokens, including particles and useful conjugated/fixed-expression chunks. Every non-English card has:

- `token`, `reading`, `romaji`;
- exactly one of `zhMeaning` and `functionZh` (particles use their function);
- `grammarStructureZh`: part of speech, conjugation/connection structure or fixed-expression role;
- optional confirmed `sourceWord` for a katakana loanword, plus provenance/status.

Import legacy `posZh` only as the fallback for absent `grammarStructureZh`. Never display a field label or automatic colon. English retains its lyric position and timing but gets no card, ruby or romaji.

Store kanji-only hiragana spans explicitly in `caption.furigana`, left-aligned to the kanji. Do not repeat kana already printed in a word; pure kana gets no ruby. For 熟字訓 use the whole kanji run with its contextual reading, and explain it in a useful card field when requested. Maintain a project-local particle-function table. Automated data is not human-confirmed.

## Preview and handoff

Render previews of the longest lyric, longest meaning, maximum-card row, mixed English, pure English, kanji readings and loanwords using real content. Card boxes remain one horizontal row. The meaning/function wraps at fixed size to at most two lines, and the grammar structure may also use two (it wraps before it shrinks); the token stays on one line. If content does not fit, report the specific field rather than adding rows or clipping.

Use the shared previewers instead of writing a project-local one:

```text
python SKILL_ROOT/scripts/render_real_previews.py PROJECT_ROOT [--run-id ID]   # setup + draft sample sets
python SKILL_ROOT/scripts/build_review_gallery.py PROJECT_ROOT [--changes FILE] # one still per row + card tables
```

`render_real_previews.py` covers the required sample list automatically (prelude, every countdown value, first sung unit, neighbours, mid-video gap, late line, tail, longest lyric, longest meaning, most cards, mixed and pure English, most ruby). `build_review_gallery.py` produces the line-by-line artifact for the user, and with `--changes` marks every proposed field change as old -> new. Both read the compiled foreground timeline, so what they show is the state the renderer really paints.

Write `deliverables/review/<slug>-review.md` grouped by stable frame IDs with provisional Chinese, card fields and only relevant unresolved issues:

```text
python SKILL_ROOT/scripts/build_review_markdown.py PROJECT_ROOT
```

It also writes `project/review/review-markdown-baseline.json` and records `reviewMarkdownSha256`, which is what lets `import_review_markdown.py` distinguish a human edit from regenerated content later (stage 4).

Set `draft_ready` after `layout-report.json` and `python SKILL_ROOT/scripts/validate_project.py PROJECT_ROOT --stage draft` pass. Stage 4 reviews linguistic content; a visually valid layout does not substitute for that review.

## Romaji overlap between neighbouring tokens

Each token's romaji is centred under that token while the lyric line draws tokens back to back with no gutter, so romaji that is wider than its token can cover its neighbour. `render_real_previews.py` measures `overlap = (romaji_left + romaji_right) - (token_left + token_right)` for every adjacent pair and fails the draft layout report above 8 px.

Since that overlap is the **sum of two adjacent deficits** `d = romaji_width - token_width`, merging the pair named in the report can move the surplus onto the *next* token instead of removing it, and the new pairing can be worse than the original. Measure the per-token deficits first, then merge a deficit with a surplus so that `d_i + d_{i+1} <= 8` holds for every pair after the merge — not simply the left pair the hint suggests. Only chunking changes; the reading, romaji and meaning of the merged range must stay correct.

Use the `renderer.font(70)` / `renderer.font(34)` sizes the report uses, and remember that a long line shrinks its lyric font (70 → 53) if any line exceeds the width budget, which would change every token width in that line.
