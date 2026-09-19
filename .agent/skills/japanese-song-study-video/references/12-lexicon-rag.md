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
| `lexicon/overrides.json` | `apply_lexicon_feedback.py` | reviewed corrections (added as variants) and reliability caps |

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

## Learning from the decision

After the user decides, convert the outcome into feedback and rebuild:

```bash
python SKILL_ROOT/scripts/apply_lexicon_feedback.py WORKSPACE_ROOT --decisions decisions.json --apply
python SKILL_ROOT/scripts/build_lexicon.py WORKSPACE_ROOT
```

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

## Rules

* Never fabricate approval: RAG reuse is still a draft until the user's content decision.
* Keep `qualityIssues` entries out of the match index; they exist as evidence only.
* Prefer `--exclude <slug>` when measuring reuse, so a project cannot match itself.
* No katakana loanword is ever invented: `sourceWord` is reused only when attested.
* A kana-only match is a candidate, never a reuse. The lexicon cannot choose between
  homophones such as 明日/未来 for `あした`.
* `lexicon/project-order.json` is what makes "newest wins" portable; keep it committed
  alongside `lexicon.json`, `feedback.json` and `overrides.json`.
