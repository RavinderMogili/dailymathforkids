# Word-problem pilot: GSM8K → Practice Mode

Pilot integration of a curated subset of GSM8K (OpenAI, MIT License; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)) into Practice Mode's
"Word Problems" content, behind a feature flag that defaults to **off**.

This directory holds the offline pipeline that produced
[`data/practice-pool-extended.json`](../../data/practice-pool-extended.json)
(100 approved questions). It is intentionally separate from the runtime app
code in `scripts/` — nothing here runs in production; it only produces a
static JSON file the app can optionally load.

## Why Practice Mode, not the Daily Quiz

The **daily quiz** (`scripts/gen_site.py`) has no concept of a curated
question bank — it asks an LLM to write 10 fresh grade-tagged questions every
morning and publishes the HTML directly. Retrofitting a static, pre-approved
question set into that pipeline would be a much larger, riskier change than
this brief calls for.

**Practice Mode** (`scripts/practice-engine.js`) already has exactly the
right shape: `data/practice-pool.json` is a static, curated JSON bank
(grade/topic/question/choices/answer/hint/steps) that `generateQuiz()` uses
100% for the "Word Problems" topic and blends up to ~40% into other topics,
with algorithmic-question fallback already built in when the pool runs
short. This pilot adds a second, clearly-labeled pool
(`data/practice-pool-extended.json`) alongside it, reusing that exact
mechanism — no new architecture.

## Pipeline

```
assess.py          → tools/word-problems/output/assessed_records.jsonl (gitignored, regenerate locally)
                    → tools/word-problems/assessment_report.json (committed summary)
adapt.py            → tools/word-problems/output/candidates.jsonl (gitignored, regenerate locally)
pick_pilot.py       → tools/word-problems/output/pilot_shortlist.json (committed)
finalize_pilot.py   → data/practice-pool-extended.json (committed, approved)
                    → tools/word-problems/output/pilot_excluded.json (committed, with reasons)
```

Run it yourself (requires a local copy of
[openai/grade-school-math](https://github.com/openai/grade-school-math)):

```bash
python tools/word-problems/assess.py --data-dir <path>/grade_school_math/data --out tools/word-problems/output
python tools/word-problems/adapt.py --in tools/word-problems/output/assessed_records.jsonl --out tools/word-problems/output/candidates.jsonl --grades 4 5 6 7 --max-per-grade 400
python tools/word-problems/pick_pilot.py --in tools/word-problems/output/candidates.jsonl --out tools/word-problems/output/pilot_shortlist.json
python tools/word-problems/finalize_pilot.py --in tools/word-problems/output/pilot_shortlist.json --approved-out data/practice-pool-extended.json --rejected-out tools/word-problems/output/pilot_excluded.json --target 100
```

`adapt.py` seeds Python's `random` with a fixed value, so distractor
generation and shortlist selection are deterministic — rerunning the exact
same commands against the exact same source files reproduces the same
`data/practice-pool-extended.json` byte-for-byte. **Re-running the full
pipeline is idempotent by construction** (it always regenerates the same
output from the same source, rather than appending); if you're instead
importing a *new* batch alongside an already-shipped one, dedupe by the
`_sourceId` field (`gsm8k-<split>-<index>`), which is stable across runs.

## What was checked automatically vs. by a human

This distinction matters — please don't read `review_status: "auto_ok"` as
"a person confirmed this question is good."

**`assess.py` (automated, full dataset, 8,792 records — every original
record in `train.jsonl` + `test.jsonl`, nothing sampled):**
- Independently re-verifies GSM8K's own `<<expr=value>>` calculator
  annotations with a restricted AST-based evaluator (no `eval`/`exec` on
  dataset text) and cross-checks the final `####` answer against the last
  verified step.
- Strips calculator annotations into kid-readable steps, fixing the case
  where deleting the annotation would glue two words together, and removing
  the rare case where GSM8K's answer text ends by echoing the question
  verbatim as a fake "step."
- Flags suitability via a conservative keyword screen (violence, drugs,
  alcohol, gambling, weapons, self-harm, and similar categories — see
  `SUITABILITY_KEYWORDS` in `assess.py`) — any hit is auto-rejected.
- Flags exact and near-duplicates (near-duplicate = shared 3-word shingles
  after normalizing numbers to a placeholder, so templated GSM8K problems
  that only change the numbers are still caught).
- Flags mixed measurement units, "about/approximately" language, and
  non-integer answers to discrete-count questions (e.g., "2.5 apples").
- Estimates a **provisional, heuristic** grade level and difficulty from
  step count, vocabulary, and a Flesch-Kincaid-style reading score. **This is
  not a curriculum mapping** — see "Grade coverage" below.

**Human review (this pilot's 130-item shortlist only, not the full 8,792 —
see "Honest scope" below):** I read every one of the 130 shortlisted
questions myself before approval. Two categories of problem showed up that
no automated check catches:

- **Rejected (3):** hidden/ambiguous assumptions or broken explanations that
  a keyword or duplicate check can't detect. Recorded with reasons in
  `MANUAL_REJECTIONS` in `finalize_pilot.py` and in
  `output/pilot_excluded.json`:
  - `gsm8k-train-00692` — silently assumes a month is exactly 4 weeks.
  - `gsm8k-train-01991` — the worked steps skip the derivation of an
    intermediate $123 total, so the final step doesn't follow from what's
    shown.
  - `gsm8k-train-01979` — a data artifact (trailing question-echo) left the
    surrounding explanation reading awkwardly even after that line was
    stripped.
- **Reworded (1):** `gsm8k-train-01480` — "twice more scoops...than Oli's"
  is genuinely ambiguous in English (could mean 2x or 3x); reworded to
  "twice as many," which is what the answer key assumes.

27 more shortlisted items weren't rejected for content — they just weren't
needed once each grade hit its 100-question-pilot capacity (`capacity_trim`
in `pilot_excluded.json`); they're reasonable candidates for a future
expansion, not excluded for quality.

## Honest scope of review

- **8,792 / 8,792** original records ran through the automated pipeline.
- **130** were hand-picked (grade/topic-balanced) and personally read
  end-to-end by me before this pilot; **100** were approved.
- The remaining ~7,900 `auto_ok` records have **only passed automated
  checks** — arithmetic is independently verified and keyword/duplicate
  screens ran, but nobody has read them for tone, realism, or
  kid-appropriateness beyond that keyword screen. Treat
  `assessment_report.json`'s counts as "passed automated gates," not
  "approved for kids." See "Remaining work" below for what expanding this
  would take.

## Dataset assessment results (full 8,792 records)

See [`assessment_report.json`](assessment_report.json) for the exact numbers
this run produced. Headline findings:

- **Split sizes:** 7,473 train + 1,319 test = 8,792 total (not exactly the
  "8.5K" the GSM8K README rounds to — counted directly from the files, not
  assumed).
- **Arithmetic:** 8,319 / 8,792 (94.6%) independently verified correct;
  473 failed automated re-verification and are auto-rejected.
- **Suitability keyword hits:** 113 records (1.3%) — auto-rejected, not
  reviewed further.
- **Duplicates:** 0 exact, 3 near-duplicates flagged by the template-shingle
  method (GSM8K is a genuinely low-duplication dataset — this is a real,
  reassuring finding, not an artifact of a weak check; see the near-duplicate
  method's limitations noted in `assess.py`).
- **Grade coverage — the most important finding:** the heuristic estimator
  produced **zero** records below grade 4. This matches GSM8K's own stated
  design goal ("a bright middle school student should be able to solve every
  problem") — it is not a bug in the heuristic. **GSM8K is not a good source
  for Grade 1-3 content.** It is a reasonable source for Grade 4-5 (this
  project's stated priority) and stretches acceptably to Grade 6-7. Grade
  8-12 estimates in the raw distribution mostly reflect "more arithmetic
  steps," not real algebra/geometry/trig curriculum content for those
  grades — GSM8K is fundamentally an arithmetic-reasoning dataset, not a
  full K-12 curriculum. **The pilot only draws from grades 4-7** for this
  reason; treat any impulse to stretch it into grades 8-12 as a curriculum
  mismatch, not a quota to fill.
- **Topics:** heavily skewed toward Money (3,600) and Time (2,473) contexts,
  with much smaller Geometry (14) and Ratios & Rates (112) representation —
  topic diversity in the pilot is deliberately capped per-topic (see
  `pick_pilot.py`) to avoid an all-money pilot set.

## Pilot composition (100 approved)

| Grade | Count |
|-------|-------|
| 4     | 32    |
| 5     | 34    |
| 6     | 20    |
| 7     | 14    |

Topic spread and five representative examples are in the top-level project
report (delivered separately). Every approved record carries `_sourceId`
(e.g. `gsm8k-train-01492`) so it can be traced back to
`output/assessed_records.jsonl` (regenerate locally) or the original GSM8K
line for audit.

## Import / enable / disable / roll back

**Import (already done for this pilot):** `finalize_pilot.py` writes
straight to `data/practice-pool-extended.json`. Re-running it from the same
shortlist overwrites that file with the same content (idempotent). There is
nothing to "import" into a database — Practice Mode reads this file
statically, same as the existing `data/practice-pool.json`.

**Enable:**
1. For **testing only**, no code change needed: open Practice Mode with
   `?enableExtendedPool=1` in the URL (e.g.
   `practice.html?enableExtendedPool=1`). This does not affect other users.
2. For **production rollout**, flip `EXTENDED_POOL_ENABLED` to `true` near
   the top of the "Extended (curated, external-dataset) word-problem pool"
   section in `scripts/practice-engine.js` and deploy. This is the single
   switch that controls the feature for everyone.

**Disable:** set `EXTENDED_POOL_ENABLED` back to `false` (or pass
`?enableExtendedPool=0` to force it off for one session/test). No data
migration needed — `data/practice-pool-extended.json` simply stops being
read.

**Roll back a specific bad question:** find its `_sourceId` in
`data/practice-pool-extended.json` and delete that one object from the JSON
array (or fix the field directly — every field is plain, editable JSON, no
DB round-trip). Redeploy the static file. There is no dependency on that
question staying anywhere else — `_userAnswer` / mistake-history rows
reference the question text and choices at answer time, not the pool file.

**Full rollback:** delete `data/practice-pool-extended.json` (or set the
flag to `false`, which is equivalent and non-destructive) — Practice Mode
falls back to exactly its pre-pilot behavior (`data/practice-pool.json` +
algorithmic generation), since `getPoolQuestions()` simply skips the
extended pool when the flag is off or the file is absent.

## Exposure tracking

GSM8K-sourced questions are finite (100 in this pilot vs. effectively
infinite algorithmic generation), so a per-browser `localStorage` list
(`dmk_extpool_seen_ids`, capped at the last 60 shown) is consulted before
each quiz is built, to avoid immediately repeating a question. If too few
unseen questions remain to fill a quiz, it safely falls back to allowing
repeats rather than ever blocking a quiz (see `preferUnseen()` in
`scripts/practice-engine.js`, and the matching Jest tests in
`scripts/practice-pool-extended.test.js`).

## Answer-key safety

Practice Mode's existing architecture is entirely client-side — the full
question object, including the correct `answer` field, ships to the browser
before the student answers (this was already true for the hand-curated pool
and algorithmic questions; this pilot does not change that pattern). This is
different from the Daily Quiz, where the API (`api/submit.js`) holds the
answer key server-side and the client never receives it before submission.
**This pilot preserves the existing Practice Mode pattern rather than
introducing a server-side answer-check for practice** — doing so would be an
unrelated architecture change out of scope for this pilot (flagged here per
the review brief's request to report differences rather than make unrelated
scoring changes).

## Remaining work to expand beyond the pilot

- **Curriculum mapping:** replace the heuristic grade estimator with an
  actual mapping against a named curriculum (e.g., the Canadian/NB math
  curriculum this project already targets) before trusting `grade_estimate`
  at scale.
- **Full-dataset human/semantic review:** the ~7,900 `auto_ok` records
  outside this 130-item shortlist have not been read by a person. Reading
  all of them at the same pace as this pilot (~130 in one focused pass)
  would take roughly 50-60 more passes of similar size — a multi-day human
  (or explicitly-approved, budgeted LLM-assisted) effort, not something to
  batch-approve automatically.
- **Bilingual content:** every pilot record ships with `questionFr: ""`
  (falls back to reading the English text aloud for the FR "Listen" button,
  which is a safe no-crash fallback already built into `practice.html`, but
  is not a real French translation). Producing verified French translations
  at scale needs either paid translation/LLM calls (requires your approval
  per the constraints on this task) or a volunteer/manual translation pass.
- **Topic labeling:** `classify_topic()` in `assess.py` is a first-match
  keyword heuristic and will occasionally mislabel a question (e.g., a
  question mentioning a birthday party being tagged "Time"). It's accurate
  enough for this pilot's topic-diversity balancing, but not precise enough
  to promise as a filter guarantee.
