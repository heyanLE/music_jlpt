# 12. Lexicon RAG: reuse cards instead of re-authoring them

Read this before stage 3 for any new project. The workspace lexicon is the reuse
layer for card content; `lexicon/README.md` documents the data model in full.

## Why

The same particles, auxiliaries and everyday words are re-authored in every song.
Reviewing them three times (lexical/grammar/translation) costs far more than
looking them up. The lexicon holds every card the workspace has ever produced and
learns from the user's decisions.

## Data

| File | Written by | Meaning |
| --- | --- | --- |
| `lexicon/lexicon.json` | `build_lexicon.py` | derived store: entries, variants, reliability, provenance |
| `lexicon/project-order.json` | `build_lexicon.py` | append-only recency order for the newest-wins conflict rule |
| `lexicon/feedback.json` | `apply_lexicon_feedback.py` | accept/reject/correction counters from the user's reviews |
| `lexicon/overrides.json` | `apply_lexicon_feedback.py` (scalar pins by hand) | reviewed corrections (added as variants), scalar dominant-value pins and reliability caps |

`lexicon.json` is derived: never hand-edit it, rebuild it.

## Drafting

```bash
python SKILL_ROOT/scripts/draft_cards_from_lexicon.py PROJECT_ROOT
```

The confidence threshold has **one** default (`lexicon_match.DEFAULT_CONFIDENCE_THRESHOLD`); do not pass a different value to the drafter than the matcher uses, or entries fall into a silent reuse gap. Re-running over an already drafted `frames.json` is refused unless `--force`, because the queue's recorded input hash would otherwise describe the previous draft.

1. Match each lyric row longest-first (`lexicon_match.py`). A longer attested chunk
   wins over a shorter one.
2. Emit `rag-reused` cards for matches the lexicon vouches for, with the entry's
   reliability and human-confirmed count in `fieldProvenance`.
3. Emit `rag-proposed-low-confidence` cards where the entry exists but is unsafe to
   assert; these are starting points, not approvals. Kana-only matches always land
   here: the lexicon cannot pick between homophones, so it offers the candidates
   (`homophoneAlternatives`) instead of deciding.
4. Write `project/review/rag-review-queue.json`: every run containing unknown text
   becomes **one phrase-level review unit** carrying the fragments the lexicon did
   recognise (with candidate glosses) and the unknown text that needs authoring. A
   phrase repeated inside one line is queued once, so the unit identity `frameId::unit`
   stays unambiguous.

Vocabulary the lexicon does not have is authored during the review, never guessed.

## Entries the lexicon refuses to match

`build_lexicon.py` quarantines entries whose stored fields cannot be trusted - whole
lyric lines stored as one "card", a `reading` holding only the first mora (`i`, `ya`,
`ko`), or a non-Japanese surface. They stay in the store as evidence with
`matchable: false` and are reported under `stats.quarantineReasons`, but they can
never win a match. A single character is matchable only when it is a real particle or
auxiliary (see `SINGLE_CHAR_FUNCTION_WHITELIST`); otherwise ragged one-character
drafts would shred real words.

## Review

New projects use **one targeted online review**, not three parallel roles:

1. Review only the queued units. Verify readings, functions and glosses against
   dictionaries, grammar references or official material; record the source and the
   exact claim it supports. Never invent a lookup.
2. Write one artifact inside the project, e.g. `project/review/online-review.json`:

   ```json
   { "schemaVersion": 1, "reviewRole": "online", "status": "completed",
     "lexiconSha256": "…", "queueSha256": "…",
     "changes": [ { "frameId": "l005", "unit": "くだらなく",
                    "resolution": "one line naming the cards it was split into",
                    "cards": [ { "token": "くだらなく", "reading": "くだらなく",
                                 "romaji": "kudaranaku", "zhMeaning": "无聊地",
                                 "grammarStructureZh": "い形容词连用形" } ],
                    "furigana": [ { "base": "愛", "reading": "いと" } ],
                    "evidence": ["https://… — supports …"] } ] }
   ```

   **Every queued unit must be answered exactly once, and no other unit may be claimed.** A unit is identified as `frameId::unit`, where `unit` is the text from `rag-review-queue.json`, and `resolution` is mandatory. Both the sealer and the render gate verify this, so an empty or unrelated review cannot stand in for a real one - that was a genuine defect once. `cards` carries the complete card set for that line (replacing the draft's fragments); `furigana` is optional and, when absent, kanji-only ruby is derived from the card readings.

   **Field discipline** (a user rule; `apply_lexicon_review.py` warns when it is broken): the meaning row carries the meaning alone. Never put the word's form or function there - `蒙上；落满（「かぶる」的过去式）` merely repeats `动词た形（过去）` and has to be `蒙上；落满`. Grammatical and functional notes belong in `grammarStructureZh`, compacted so the one-line grammar field still fits (`名词＋格助词（标记动作对象）`). A particle's `functionZh` says what the particle does (`表示自问`), while a structural fragment (`与「な」组成「かな」`, `接意志形`) belongs in the grammar field as well. A katakana loanword also carries `sourceWord`, which the renderer prints above the token.

   **Terminology the user requires**:
   * verb classes are named `第一类动词` / `第二类动词` / `第三类动词` - never `动词（五段）`, `（一段）`, `（サ変）`, `（カ変）`;
   * never write `存续体` (or `存続体`) as a label; write the actual 接续, e.g. `动词て形＋补助动词「いる」`;
   * a contracted form (`てる`, `てく`) must state the contraction in the grammar field, e.g. `动词て形＋补助动词「いる」（口语约音「てる」）`; if the full wording does not fit the card width, shorten the wording rather than dropping the note.
   * a particle's function states the actual role in that line (`提示动作发生的场所`), never a different line's role.

3. Seal it: `python SKILL_ROOT/scripts/seal_lexicon_review.py PROJECT_ROOT --online-review project/review/online-review.json`.
   The audit pins the lexicon revision, the review queue, the review artifact, the frame count, the draft's card count and the answered-unit count. The render gate re-derives all of that from disk, so a hand-written audit fails.
4. Install the reviewed content: `python SKILL_ROOT/scripts/apply_lexicon_review.py PROJECT_ROOT`. It refuses a review that is not the sealed one or that does not answer the queue, validates every card against the renderer's rules (token present in the line in order, exactly one of `zhMeaning`/`functionZh`, no serialized separator, ruby anchors matching the lyric), replaces each reviewed line's cards, promotes the remaining pre-fill to `rag-reused`, and writes `project/review/rag-review-merge-log.json` with both frame hashes.

Existing projects that already carry a sealed three-role audit keep working: the
render gate accepts `mandatory-multi-agent` and `lexicon-rag-targeted-online`
alike. Both modes require the user's verbatim `userWording` (a generic
`authorization` field is not accepted), reject rehearsal or placeholder wording,
and require the audit's sealed draft to be a real recorded ancestor of the frames
being rendered.

## Correcting a row the queue never covers

`lexicon_match` queues a row only when it contains text the lexicon cannot resolve. A row
whose every span is a lexicon match produces **no review unit at all**, even when each span
is flagged `needsReview` because the entry carries several attested senses. Such a row is
drafted from the entry's dominant value, promoted to `rag-reused` when the review is
applied, and can only be caught by the user reading the previews.

A correction to one of those rows cannot travel through the online review - the sealer and
the render gate both reject a unit that was never queued - so it goes through the guarded
change set instead:

```bash
python SKILL_ROOT/scripts/apply_review_merge.py --project-root projects/<slug> \
    --user-wording "VERBATIM" --scope "all 35 frames (l001-l035)"
```

`project/review/accepted-changes.json` carries `baseFrameSha256`, `confirmAllFrames: true`
and one `set` (`{frameId, field: "grammarCards[1].zhMeaning", old, new}`) or `mergeCards`
(`{frameId, indices, expectedTokens, newCard}`) operation per change. Every `old` value and
`expectedTokens` list is verified before anything is written, so a stale change set fails
instead of silently overwriting reviewed content. Operations are applied in order against the
same mutating frame, so when one row needs both a `mergeCards` and a `set`, list the `set`
first and index it against the *pre-merge* card list (`mergeCards` removes the merged
positions and reinserts one card at `indices[0]`, shifting every later index). `--accepted` resolves against the current
directory, so omit it and let the default under the project root apply. The merge also
writes `merge-log.json` and `review-decision.json` (the two files the render gate reads)
and stamps `human-confirmed` on every card, so run it only once the user has accepted the
content. Record the change set in `build-state.json` as well: a later
`draft_cards_from_lexicon.py --force` overwrites the frames, and the change set must then be
re-applied. Convert the same correction into lexicon feedback so the entry is flagged on
its next reuse.

## Learning from the decision

After the user decides, convert the outcome into feedback and rebuild:

```bash
python SKILL_ROOT/scripts/apply_lexicon_feedback.py WORKSPACE_ROOT --decisions decisions.json --apply
python SKILL_ROOT/scripts/build_lexicon.py WORKSPACE_ROOT
```

Add `--allow-new` when the decision covers a merged chunk that is not in the published
lexicon yet (drop it for a plain dry run first: the script refuses unknown surfaces so a
typo cannot create a phantom entry).

* **accepted** → the entry's reliability rises (it will auto-reuse next time);
* **corrected** → recorded as its own signal plus an extra attested *variant* (a
  particle such as で keeps every function; a correction never overwrites the entry,
  and it never counts as an accept);
* **rejected** → reliability falls, and while rejections outnumber accepts the entry
  is pinned at 0.3 so it stops auto-reusing. Scoring is by **net** outcome, so an
  entry the user later accepts repeatedly recovers instead of being pinned forever by
  an old rejection.

Feedback for a surface that is not in the published lexicon is refused unless
`--allow-new`, so a typo cannot create a phantom entry.

### What a correction actually moves

A correction is an extra attested variant, never a replacement, and
`build_lexicon.variant_rank` refuses to promote a value that exists *only* because of a
reviewed correction - so writing the feedback is not the same as changing the dominant
value a later draft reuses. What moves a dominant is the project's own frames: they
carry the corrected value as `human-confirmed`, and frame + correction beats the older
unconfirmed attestations.

* Say what will move before promising the user a fix. In the 僕と三原色 round the
  corrected ように (meaning and grammar) and 忘れない (grammar) took over their dominant
  fields with no extra step, while ない kept 没有 / 形容词: the leading values carried 6
  and 23 attestations against the 2 the correction added. That is a prefill problem, not
  a silent-wrong-card problem - an entry with several attested meanings is never
  auto-reused (confidence caps at 0.6, under the 0.75 reuse threshold) and the
  corrected value is listed in `alternateMeanings`.
* **A scalar override is the only thing that outranks frequency**, and it is what to
  reach for when the losing value is just a lead built by dirty drafts. Write the
  decision in the scalar form of `lexicon/overrides.json`, keeping any `corrections`
  entries for provenance:

  ```jsonc
  "ない": { "meaning": "不……（否定）", "grammar": "否定助动词；「聞いてない」＝「聞いていない」的口语省略" }
  ```

  `build_lexicon.variant_rank` ranks a pinned value first, so it wins `dominant*` with a
  fraction of the attestations, and `lexicon.json` marks the record `"pinned": true`
  beside the value that leads on count. State two consequences when you use one: the pin
  rewrites the prefill of **every** later project until it is edited out (nothing removes
  it automatically), and a pinned `grammar` is what `is_function_entry` reads - pinning
  a particle/auxiliary reading re-classifies the entry and raises its ambiguity penalty
  (ない fell 0.74 -> 0.55), which is the intended direction: an ambiguous auxiliary must
  not be auto-reused. Confirm the pin moved what you claim by rebuilding to a temporary
  `--out` path and diffing `dominant*` against the published file.
* A merged chunk is the reliable fix for a wrongly split word: the new entry
  (`こんなん`, `見てる`, `ても`, `鬱向いて`) is `human-confirmed`, reliability 0.9,
  auto-fillable, and the longest-match rule makes it beat the old こんな + ん split in
  every later project.
* Do not record feedback for a card whose wording came from the first draft or the
  online review rather than from the lexicon - a near-duplicate variant on a particle
  costs 0.05 reliability and buys nothing.
* `apply_lexicon_feedback.py` accepts `kind` as a correctable field, but
  `build_lexicon.py` only folds corrections to `VARIANT_FIELDS` (meaning, grammar,
  reading, romaji) - a `kind` correction is logged in `overrides.json` and then ignored,
  so the entry keeps its old word class (and its old ambiguity penalty).

### Rebuilding has two side effects

`build_lexicon.py` rewrites `lexicon/lexicon.json`, and that file is the revision
`verify_render_gate.py` binds as `lexiconSha256`. Rebuilding after a delivery makes
`validate_project.py --stage render` report `Render authorization hash missing or stale:
lexiconSha256` (setup and draft still pass; the delivered video, manifest and QA are
unaffected). Say so when you offer the rebuild; the authorized revision is the committed
blob, recoverable with `git show HEAD:lexicon/lexicon.json`.

A rebuild also folds in **every** project whose `project/frames.json` is newer than the
published lexicon, not just the one you are reporting on - in that round 89 surfaces
appeared and 34 dominant values moved, including entries from unrelated songs. Build to a
temporary path with `--out <file inside the workspace>` and diff it against the published
file before promoting, so the scope you report is the real one.

## Rules

* Never fabricate approval: RAG reuse is still a draft until the user's content decision.
* Keep `qualityIssues` entries out of the match index; they exist as evidence only.
* Prefer `--exclude <slug>` when measuring reuse, so a project cannot match itself.
* No katakana loanword is ever invented: `sourceWord` is reused only when attested.
* A kana-only match is a candidate, never a reuse. The lexicon cannot choose between
  homophones such as 明日/未来 for `あした`.
* `lexicon/project-order.json` is what makes "newest wins" portable; keep it committed
  alongside `lexicon.json`, `feedback.json` and `overrides.json`.
