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

## Three distinct review tiers — do not conflate them

This project used **two** of three possible review tiers. Neither
`review_status: "auto_ok"` nor anything else in this pipeline should be read
as "a teacher confirmed this question is good" — that tier was never used.

1. **Automated checks** (`assess.py`/`adapt.py`) — deterministic code, no AI
   involved at all. Full dataset, all 8,792 records. Described in detail
   below.
2. **AI semantic review** — a Claude session (this one) reading questions
   and judging them the way an LLM does: fast, consistent about the checks
   it's explicitly told to look for, but not a substitute for subject-matter
   or child-development expertise, and not infallible (see the mg/ml example
   below, which an earlier pass of this same review missed). Applied to a
   130-item shortlist only, **not** the full 8,792 — see "Candidate funnel"
   below.
3. **Human / teacher review** — a qualified person (teacher, curriculum
   specialist, parent reviewer) reading and judging the content. **Not
   performed on any record in this pipeline.** If you see "reviewed" or
   "approved" language anywhere in the app, docs, or UI referring to this
   content, it means tier 1 + tier 2 above — flag it if it ever gets
   rephrased to imply tier 3 happened.

### Tier 1: automated checks (all 8,792 records)

- Independently re-verifies GSM8K's own `<<expr=value>>` calculator
  annotations with a restricted AST-based evaluator (no `eval`/`exec` on
  dataset text) and cross-checks the final `####` answer against the last
  verified step. **See "What arithmetic verification does and does not
  prove" below — this is a narrower guarantee than it sounds.**
- Strips calculator annotations into kid-readable steps, fixing the case
  where deleting the annotation would glue two words together, and removing
  the rare case where GSM8K's answer text ends by echoing the question
  verbatim as a fake "step."
- Flags suitability via a conservative keyword screen (violence, drugs,
  alcohol, gambling, weapons, self-harm, and similar categories — see
  `SUITABILITY_KEYWORDS` in `assess.py`) — any hit is auto-rejected. This is
  a keyword screen, not semantic content judgment — it catches the word
  "beer" but not, say, a subtly age-inappropriate scenario that uses none of
  the listed words.
- Flags exact and near-duplicates (near-duplicate = shared 3-word shingles
  after normalizing numbers to a placeholder, so templated GSM8K problems
  that only change the numbers are still caught).
- Flags mixed measurement units, "about/approximately" language, and
  non-integer answers to discrete-count questions (e.g., "2.5 apples").
- Estimates a **provisional, heuristic** grade level and difficulty from
  step count, vocabulary, and a Flesch-Kincaid-style reading score. **This is
  not a curriculum mapping** — see "Grade classification" below for exactly
  what the heuristic does and does not establish.

### Tier 2: AI semantic review (130-item shortlist only)

I (an AI/LLM, not a human reviewer) read every one of the 130 shortlisted
questions myself before approval — checking things automated code can't:
does the wording make sense, does the explanation actually justify the
answer, is anything subtly off. This caught two categories of problem:

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
- **Reworded (2, both still approved and included in the 100 — see
  "Candidate funnel" below):**
  - `gsm8k-train-01480` — "twice more scoops...than Oli's" is genuinely
    ambiguous in English (could mean 2x or 3x); reworded to "twice as many,"
    which is what the answer key assumes.
  - `gsm8k-train-01110` — asked for the answer "in milligrams" but every
    worked step computes milliliters (a 5 ml/kg dosing instruction). **This
    one was missed on the first AI-semantic-review pass** and only caught
    later, while re-reading records to assemble example output for a
    report. It's a concrete illustration of tier 2's real failure rate: even
    a careful LLM read-through misses things, and this pipeline has no
    tier-3 check that would have been a second backstop.

27 more shortlisted items weren't rejected for content — they just weren't
needed once each grade hit its 100-question-pilot capacity (`capacity_trim`
in `pilot_excluded.json`); they're reasonable candidates for a future
expansion, not excluded for quality.

## What arithmetic verification does and does not prove

"8,319 / 8,792 records passed arithmetic verification" is a real, useful
number — but it proves less than it sounds like. Precisely, `assess.py`'s
`verify_annotations()` checks two things:

1. Every `<<expr=value>>` annotation in GSM8K's own answer text: does `expr`
   actually evaluate to `value`? (Restricted AST evaluator, not `eval`.)
2. Does the final `####` number match the last annotation's computed value?

**What this does NOT check:** whether the sequence of calculations the
answer chose is the mathematically correct way to answer the question that
was actually asked. A record can pass both checks above while still solving
the wrong problem — for example, if a question asks for the difference
between two quantities and the answer text confidently adds them instead,
every annotation can still be internally arithmetically consistent (the
addition is computed correctly) while the answer is conceptually wrong for
the question posed. Nothing in tier 1 catches that class of error — only
tier 2 (reading the question and the steps together, which is what caught
the `gsm8k-train-01991` rejection above) or a real tier-3 review would.

**Known gaps in the check itself, not just its scope:**
- When a record has **zero** calculator annotations, `arithmetic_verified`
  is set `True` as long as a `####` answer parses — i.e., "nothing to
  contradict" is treated as a pass. This is a real gap, not a deliberate
  design choice: a small number of GSM8K answers compute their final step
  without an annotation, and the current check cannot verify those at all.
- The "final answer matches last annotation" check assumes the very last
  annotated calculation *is* the one that produces the final answer, which
  is true for the overwhelming majority of GSM8K's format but not
  guaranteed by anything structural.

**Bottom line:** treat "arithmetic verified" as "the annotated calculations
are internally self-consistent," not "this solution correctly solves this
problem." The latter claim requires tier 2 or tier 3 review, and — per the
"Candidate funnel" section below — only 100 of the 8,792 records have had
either.

## Grade classification: method and honest limits

`grade_estimate` comes from a single heuristic formula in `assess.py`
(`assess_record()`):

```
score = step_count
        + (2 if percent/fraction language present else 0)
        + (1 if a decimal number appears else 0)
        + max(0, (flesch_kincaid_grade_level - 3) / 2)
grade_estimate = clamp(round(2 + score), 2, 12)
```

This is a readability/complexity proxy, not a curriculum alignment check —
it has never been validated against an actual Grade 1-12 curriculum
document, and nothing in this pipeline claims otherwise. **Grades 4-7 are
just as provisional as any other grade estimate this formula produces** —
they were chosen as the pilot's range because they're where the *volume* of
estimated-complexity landed for this dataset, not because they've been
independently confirmed correct.

**What this assessment actually found, stated precisely:** across all 8,792
records, this specific heuristic formula assigned zero records to Grade 1,
2, or 3. Tier 2 (AI semantic) review of the 130-item shortlist — which was
itself drawn only from the estimator's Grade 4-7 output — did not surface
anything that read as Grade 1-3-appropriate either.

**What that finding does not establish:** it is not proof that GSM8K
contains no Grade 1-3-appropriate material anywhere in its 8,792 records.
The heuristic was never tuned or validated to detect early-elementary
reading levels specifically, no one read the `rejected`/`needs_review`
records (which weren't grade-estimated for this purpose) looking for
simple ones, and a different classification method could plausibly find
some. What can be said with more confidence: GSM8K's own README states its
target is "a bright middle school student," which is at least directionally
consistent with this heuristic's output — but that's corroborating context,
not independent proof. Treat "no Grade 1-3 content in the pilot" as this
assessment's finding, not a settled fact about the dataset.

## Candidate funnel: 8,792 → 130 → 100

| Stage | Count | What happened |
|---|---:|---|
| Original dataset (train + test) | 8,792 | Every record, tier 1 (automated) only |
| `auto_ok` after tier 1 | 8,053 | Passed all automated checks — **not** tier-2/3 reviewed |
| Grade 4-7 candidates generated | 1,600 | `adapt.py`, capped at 400/grade |
| Shortlisted for tier 2 (AI semantic) review | 130 | `pick_pilot.py`, grade/topic-balanced |
| Rejected in tier 2 | 3 | Content problems — see above |
| Reworded in tier 2 (still approved) | 2 | Wording fixes — see above |
| Trimmed for pilot capacity (not a quality rejection) | 27 | `capacity_trim` in `pilot_excluded.json` |
| **Approved into the pilot** | **100** | `data/practice-pool-extended.json` |

Both reworded records (`gsm8k-train-01480`, `gsm8k-train-01110`) are
included in the 100 approved, with their corrected wording — they were
never in the "rejected" 3.

### Five complete approved examples

| Source ID | Grade | Question | Choices | Answer | Explanation (steps) |
|---|---|---|---|---|---|
| `gsm8k-train-02090` | 4 | A bag full of sugar weighs 16 kg. A bag full of salt weighs 30 kg. If you remove 4 kg from the combined weight of these two bags, how much do the bags now weigh? | 84, 38, 50, **42** | 42 | The bags together weigh 16 + 30 = 46 kg. → Removing the 4 kg, the bags will weigh 46 − 4 = 42 kg. |
| `gsm8k-train-00677` | 5 | Mr. Caiden wants to do repairs to his house and requires 300 feet of metal roofing. Each foot costs $8, and the supplier brings in 250 feet for free. How much must Mr. Caiden pay for the remaining metal roofing? | 50, 300, 200, **400** | 400 | The supplier brought 300 − 250 = 50 fewer feet. → Mr. Caiden pays for the remaining 50 feet: 50 × $8/foot = $400. |
| `gsm8k-train-00539` | 6 | A paper company plants 3 trees for every tree they chop down. They chopped 200 trees in the first half of the year and 300 more in the second half. How many more trees do they need to plant? | 1350, 1050, 1875, **1500** | 1500 | They chopped 200 + 300 = 500 trees total. → They plant 3 trees per tree chopped: 500 × 3 = 1500 trees. |
| `gsm8k-train-01077` | 7 | Louie obtained 80% on a math quiz. He had 5 mistakes. How many items were there on the math quiz? | **25**, 31, 50, 32 | 25 | 100% − 80% = 20% of items were wrong, which is 5 items. → 1% = 5/20 = 1/4 of an item. → Total items (100%) = 1/4 × 100 = 25. |
| `gsm8k-train-01110` | 6 | A doctor needs to give medicine to a child... for every kilogram of weight, 5 ml of medicine. The child weighs 30 kg and the full dose is given in 3 equal parts. How many **milliliters** will each part of the dose be? *(reworded from "milligrams" — see tier 2 notes above)* | **50**, 450, 100, 55 | 50 | Total needed: 30 kg × 5 ml/kg = 150 ml. → Each dose: 150 ml / 3 doses = 50 ml/dose. |

## Honest scope of review

- **8,792 / 8,792** original records ran through tier 1 (automated checks).
- **130** were hand-picked (grade/topic-balanced) and went through tier 2
  (AI semantic review, performed by this Claude session); **100** were
  approved.
- **0** records have had tier 3 (human/teacher) review.
- The remaining ~7,900 `auto_ok` records have **only passed tier 1** —
  arithmetic self-consistency is checked and keyword/duplicate screens ran,
  but no one and nothing has read them for whether they solve the right
  problem, for tone, realism, or kid-appropriateness beyond the keyword
  screen. Treat `assessment_report.json`'s counts as "passed automated
  gates," not "approved for kids." See "Remaining work" below for what
  expanding this would take.

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
  (see "Grade classification: method and honest limits" below for exactly
  what it does and doesn't establish) produced **zero** records below grade
  4 out of 8,792. Grade 8-12 estimates in the raw distribution mostly track
  "more arithmetic steps," not real algebra/geometry/trig curriculum content
  for those grades — GSM8K is fundamentally an arithmetic-reasoning dataset.
  **The pilot only draws from grades 4-7**, and even that range is a
  provisional heuristic estimate, not a curriculum-validated placement;
  treat any impulse to stretch into grades 8-12 as a mismatch between this
  dataset's actual content and those grades' real curricula, not a quota
  to fill.
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

Five complete examples (question, all choices, answer, and explanation) are
in "Candidate funnel" above. Every approved record carries `_sourceId`
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
1. For **local/dev testing only**, no code change needed: open Practice
   Mode with `?enableExtendedPool=1` in the URL on a local/dev host (e.g.
   `http://localhost:8080/practice.html?enableExtendedPool=1`, or a `file://`
   preview). `isLocalDevHost()` in `scripts/practice-engine.js` gates this —
   the query param is **silently ignored on any other hostname**, including
   the production domain, so a visitor to the live site cannot self-enable
   this by editing the URL. See the "query param is IGNORED on a
   production-looking hostname" and "ignored on any non-dev hostname" Jest
   tests for this guarantee.
2. For **production rollout**, flip `EXTENDED_POOL_ENABLED` to `true` near
   the top of the "Extended (curated, external-dataset) word-problem pool"
   section in `scripts/practice-engine.js` and deploy. This is the single
   switch that controls the feature for everyone.

**Disable:** set `EXTENDED_POOL_ENABLED` back to `false`. On a local/dev
host you can also pass `?enableExtendedPool=0` to force it off for one
session/test. No data migration needed —
`data/practice-pool-extended.json` simply stops being read.

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

## Exposure tracking, and its real limits

GSM8K-sourced questions are finite (100 in this pilot vs. effectively
infinite algorithmic generation), so a per-browser `localStorage` list
(`dmk_extpool_seen_ids`, capped at the last 60 shown) is consulted before
each quiz is built, to avoid immediately repeating a question. If too few
unseen questions remain to fill a quiz, it safely falls back to allowing
repeats rather than ever blocking a quiz (see `preferUnseen()` in
`scripts/practice-engine.js`, and the matching Jest tests in
`scripts/practice-pool-extended.test.js`).

**This is a per-browser convenience, not a real dedup guarantee.** Being
explicit about what it cannot do:
- **Does not** persist across devices — a student practicing on a phone and
  a laptop has two independent `dmk_extpool_seen_ids` lists.
- **Does not** survive cleared site data, a different browser, or a private/
  incognito window — each starts with an empty seen-list.
- **Does not** coordinate across multiple students sharing a device/browser
  profile without separate logins — they share one `localStorage`, so one
  student's "seen" list affects what the other is offered.
- Only reduces the *frequency* of repeats for a single browser profile over
  time; it was never intended to and does not guarantee a question is never
  shown twice.

**What the pool architecture does guarantee** (verified with tests against
the real `data/practice-pool-extended.json`, not just reasoning about the
code — see "real approved-pool data integrity guarantees" in
`scripts/practice-pool-extended.test.js`):
- An out-of-range grade request (1-3, 8-12) never surfaces an extended-pool
  question, because `getPoolQuestions()` filters strictly on `q.grade` and
  no approved record exists outside grades 4-7 — this holds regardless of
  exposure-tracking state.
- A non-"Word Problems" topic request never surfaces an extended-pool
  question, for the same reason (every approved record's `topic` field is
  exactly `"Word Problems"`).
- No candidate, rejected, or capacity-trimmed record can ever be served —
  the app only ever fetches `data/practice-pool-extended.json` itself; there
  is no code path that reads `output/candidates.jsonl`,
  `output/pilot_excluded.json`, or `output/pilot_shortlist.json` at runtime
  (also asserted directly in the test suite by checking `practice-engine.js`
  never references those filenames).
- The algorithmic fallback path (used when too few pool questions match a
  request) draws from the same pre-existing per-grade topic generators as
  before this pilot — it has no awareness of or dependency on the extended
  pool, so it can't leak unapproved content either.

## Practice scoring trust boundary

This section documents an existing, pre-pilot gap in Practice Mode's
scoring architecture — precisely, not just in outline — because practice
points feed into rewards (Math Stars, the 300-Point Club) and the review
brief specifically asked for the request payload and trust boundary to be
spelled out.

### The exact request/response contract

`practice.html` tallies `practiceState.correct`/`practiceState.count`
entirely client-side (comparing the student's clicked choice against the
`answer` string baked into that question's `onclick` handler at render
time — the correct answer is present in the page's DOM/HTML for every
question, visible via view-source, for every source: hand-curated pool,
algorithmic, and this pilot's extended pool alike). `showResults()` then
calls `submitPracticeScore(correct, total, timeSeconds, pointsEarned)`,
which POSTs to `/api/practice-submit` with:

```json
{ "userId": "...", "correct": 8, "total": 10, "difficulty": "easy",
  "topics": ["Word Problems"], "timeSeconds": 142, "pointsEarned": 4,
  "wrongAnswers": [ /* question text/choices/hint for mistake-review only */ ] }
```

`api/practice-submit.js` (in the API repo):
- **Ignores** the client-supplied `pointsEarned` entirely and recomputes
  `rawPoints = Number(correct) * 0.5` from the client-supplied `correct`.
- **Does not** receive, and has no code path to receive, any per-question
  identifier or the student's actual selected answers matched against a
  server-held answer key. `wrongAnswers` is written to the `mistakes` table
  for the review feature and is never used to cross-check `correct`.
- **Does** independently enforce a real limit: it queries the
  `practice_submissions` table for the last 36 hours, computes `usedToday`
  from those real rows (not from anything the client sends), and caps
  `pointsEarned` at `10 − usedToday`.

**Net effect:** the server verifies *how many points remain available today*
against real data, but trusts the client's claim of *how many questions were
answered correctly* completely. Server-side recomputation of points from
`correct` does **not** mean the server independently verified which answers
were correct — those are two different claims, and only the first one is
true here. A user (or anyone who can reach the endpoint with a valid
`userId`) could call `/api/practice-submit` directly with a fabricated
`correct` value and no prior quiz activity at all, and receive points up to
the same 10/day cap a legitimate session would. **This is identical for
every practice question source — the hand-curated pool, algorithmic
generation, and this pilot's extended pool all go through the exact same
endpoint and the exact same trust boundary. This pilot does not create,
worsen, or fix this gap.**

### What this pilot does about it (and what it explicitly does not do)

Given the choice between (a) building server-side per-question verification
for practice scoring, or (b) excluding this pilot's content from
point-earning until that exists, this pilot takes option (b), scoped as
narrowly as possible:

- `computePointsEligibleTally()` in `scripts/practice-engine.js` computes a
  *separate* tally that excludes any question with `_source === 'gsm8k'`
  from both the correct-count and the total used for the points
  calculation and the `/api/practice-submit` payload. Students still see
  and answer these questions normally, with normal per-question feedback —
  they just don't count toward points sent to the server.
- Practice Mode's results screen shows a note — "*Some preview questions in
  this set don't earn points yet*" — whenever any question was excluded
  this way, and the points figure shown on screen is the exact same number
  computed for (and sent to) the server; see "Displayed vs. submitted
  totals" below for how that's verified.

**This is a client-side convenience, not a security control, and must never
be described as one.** It changes what a well-behaved browser running the
real app *sends*; it does nothing to what `/api/practice-submit` *accepts*.
Anyone who could already fabricate a `correct` value for hand-curated or
algorithmic questions (the pre-existing gap above) can fabricate one that
ignores this exclusion just as easily — the endpoint has no way to know
whether a submitted `correct` count came from GSM8K questions, other
questions, or no questions at all. The only real fix is server-side: give
`/api/practice-submit` a way to verify individual answers against a
question source it controls. For this pilot's finite, static, 100-question
pool that's tractable (the API could bundle a copy of
`data/practice-pool-extended.json` and verify `{sourceId, submittedAnswer}`
pairs against it) — for the hand-curated pool it's the same shape of fix,
and for algorithmically-*generated* questions it's harder, since the server
would need to either regenerate and check the exact question server-side or
sign/verify tokens per generated question. That full fix is future work,
tracked in "Remaining work" below, not attempted in this pilot.

### Displayed vs. submitted totals agree, by construction

`showResults()` computes `tally = computePointsEligibleTally(...)` once,
then uses `tally.correct`/`tally.total` both to compute `pointsEarned` for
on-screen display **and** as the exact `correct`/`total` arguments passed to
`submitPracticeScore(...)`. There's no separate code path that could let the
screen show one number while a different one is sent. This is covered by
the `points-eligible tally` Jest tests in
`scripts/practice-pool-extended.test.js`, run locally (mocked, no network —
see "Local verification" below).

One pre-existing (not pilot-introduced) source of possible display/server
disagreement remains, for completeness: the on-screen daily-cap remaining
amount is estimated from a client-side `localStorage` counter, while the
server computes its cap from real `practice_submissions` rows. These can
drift apart if, for example, `localStorage` is cleared mid-day or the
student switches devices — the server's number is always the one that
actually governs points awarded; the client's is a best-effort preview. This
is an existing characteristic of the daily-cap UI, not something this pilot
changed.

## Remaining work to expand beyond the pilot

- **Server-side practice answer verification** (see "Practice scoring trust
  boundary" above): the highest-priority follow-up if this pilot is meant to
  earn points, not just the highest-priority GSM8K-specific item. Scoped
  smallest-first: verify extended-pool answers server-side (finite, static,
  100 questions, easy to bundle into the API); the hand-curated pool is the
  same shape of fix; algorithmic questions need a different approach
  (regenerate-and-check, or signed per-question tokens).
- **Human/teacher review**: zero records in this dataset have had tier-3
  (qualified-person) review. If any content here needs to be described as
  "teacher-reviewed" or "teacher-approved" to parents/schools, that review
  needs to actually happen first — this pipeline does not perform it.
- **Curriculum mapping:** replace the heuristic grade estimator with an
  actual mapping against a named curriculum (e.g., the Canadian/NB math
  curriculum this project already targets) before trusting `grade_estimate`
  at scale.
- **Full-dataset AI semantic (and, ideally, human/teacher) review:** the
  ~7,900 `auto_ok` records outside this 130-item shortlist have had neither.
  Reading all of them at the same pace as this pilot's AI semantic review
  (~130 in one focused pass) would take roughly 50-60 more passes of similar
  size — a multi-day effort requiring your explicit approval before running
  (whether done as further AI-assisted passes or handed to a human/teacher
  reviewer), not something to batch-approve automatically. AI semantic
  review alone, however thorough, is not a substitute for human/teacher
  review if this content is ever represented to parents/schools as
  teacher-vetted.
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
