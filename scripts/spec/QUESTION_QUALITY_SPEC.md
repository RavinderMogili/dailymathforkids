# Canonical Question Quality Specification

Version: 1
Status: normative for Phase 0
Derived from: DailyMathForKids Question Quality Master Blueprint v1.0, sections 2, 7, 8

This file is the single source of truth for how a question is parsed, normalized,
compared, solved and judged. Every implementation — the Python daily validator and
the JavaScript practice-engine harness — must implement exactly this document, and
both must reproduce `conformance-fixtures.json` byte-identically. If the two
implementations disagree on any fixture, CI fails. No implementation may add,
relax or reinterpret a rule locally; changes happen here first.

## 1. Verdicts

Every question receives exactly one verdict.

| Verdict | Meaning | Publishable |
|---|---|---|
| `VALID` | All applicable structural gates pass **and** an independent solver reproduced the stated answer. | yes |
| `UNVERIFIED` | Structural gates pass, but no independent solver covers this question. | **no** |
| `ERROR` | Any structural gate failed, or the solver contradicted the stated answer. | **no** |

`UNVERIFIED` is never equivalent to `VALID`. A question is not publishable because
its stored answer happens to appear among its choices. The publication gate is
fail-closed: it blocks unless the verdict is `VALID`, or the item is listed in an
explicit human review manifest (`data/review/verified-items.json`) recording the
reviewer, the date, the worked verification and the reason.

The maximum number of non-`VALID` items permitted in a publication run is a policy
knob whose default is `0`.

## 2. Canonical value model

All comparison happens on canonical values, never on strings. Numbers are exact
rationals — never floats — so the two implementations cannot drift through
floating-point rounding. `den` is always positive and `gcd(|num|, den) == 1`.

```text
number       { kind: "number",   num: int, den: int }
percent      { kind: "percent",  num: int, den: int }              # 25% -> 25/1
currency     { kind: "currency", num: int, den: int, symbol: str } # $1.50 -> 3/2
measurement  { kind: "measurement", num: int, den: int, unit: str }
fraction     { kind: "number", num, den }        # a fraction IS a number
ratio        { kind: "ratio", terms: [int, ...] }                  # reduced
time         { kind: "time", minutes: int, meridiem: "AM"|"PM"|null }
quotrem      { kind: "quotrem", q: int, r: int }                   # "51 R3"
text         { kind: "text", value: str }                          # casefolded, collapsed spaces
```

A parsed value additionally retains the form as written, so that lowest-terms and
denominator gates can judge the authored surface form while comparison uses the
reduced value: `written_num` / `written_den` for anything authored as `a/b`
(`3/9` canonicalizes to `1/3` with `written_num: 3, written_den: 9`), and
`written_decimals` for a decimal's authored precision.

Unit strings are canonical and case-sensitive: `cm`, `m`, `km`, `mm`, `g`, `kg`,
`mL`, `L`, `cm2`, `m2`, `cm3`, `m3`, `deg`, `degC`, `min`, `h`, `s`. Superscript
input (`cm²`, `cm³`) and `°`/`°C` normalize to `cm2`, `cm3`, `deg`, `degC`.
`cents` and `¢` normalize to `currency` with symbol `¢`. Bare `$` before or after
the number normalizes to symbol `$`.

## 3. Parsing

Parsing is deterministic and total: an input either parses to exactly one canonical
value or yields `PARSE_FAILED`. Parsing never guesses between two candidate types.

Recognized surface forms, in this precedence order:

1. `time` — `H:MM` or `H:MM AM|PM`, `H AM|PM`. `12:00 AM` is minute 0.
2. `quotrem` — `<int> R<int>`, `<int> remainder <int>`.
3. `ratio` — `<int>:<int>(:<int>)*` that is not a valid `time`.
4. `percent` — trailing `%`, optional space.
5. `currency` — leading `$`/`£`/`€`, or trailing `$`/`cents`/`¢`.
6. `measurement` — number followed by a recognized unit.
7. `number` — integer, decimal, or `<int>/<int>`; optional `,` thousands
   separators; optional leading sign; optional mixed number `<int> <int>/<int>`.
8. `text` — anything else.

Rule 8 is a genuine catch-all. A typed pattern applies only when it consumes the
**entire** trimmed input; if any characters remain, the value is `text`. Prose that
happens to contain digits or a unit — `The blue ribbon, by 7 cm`, `3 tenths`,
`x = 4, y = 0` — is `text`, and two such answers compare by canonical text
equality. `PARSE_FAILED` is reserved for empty input, placeholder tokens and a
zero denominator; it must never be produced merely because a typed pattern did not
match.

A string that could be read as two different types is a parse ambiguity and is an
`ERROR` (`AMBIGUOUS_ANSWER_FORM`), never a silent choice. `2:3` is a `ratio`;
`2:30` with no meridiem is a `time`; the ambiguity is resolved by the rule that a
second component in `0..59` with two digits is a time and a single digit is a
ratio, so `2:3` is a ratio and `2:03` is a time.

## 4. Normalization (value-preserving only)

A normalizer may only produce a canonical value from a surface form. It must never
write a new surface form back into content, never choose between candidates, and
never change a mathematical value. Permitted, because provably value-preserving:

- collapse and trim whitespace; remove `,` thousands separators
- drop trailing `.` and insignificant trailing zeros (`12.50` = `12.5` = `25/2`)
- accept `$5` / `5 $` / `5 dollars` as the same currency value
- accept `50 %` as `50%`
- reduce a fraction to lowest terms *for comparison purposes*
- casefold and collapse whitespace for `text`

Explicitly forbidden, because value-changing (each is a hard `ERROR`):

- adding or removing a unit (`5` → `5 cm`) — `UNIT_ASSERTION`
- adding or removing a currency symbol where the value changes meaning
  (`70` → `70 cents` when the item's unit is dollars) — `UNIT_ASSERTION`
- reinterpreting an integer as a fraction, ratio or time (`3` → `3/4`,
  `2` → `2:3`, `830` → `8:30`) — `VALUE_CHANGED`
- extending an answer with additional text (`B` → `Both A and B`,
  `4` → `4 candies, 4 left`) — `VALUE_CHANGED`
- selecting a choice because it shares a prefix with the stored answer —
  `PREFIX_SUBSTITUTION`, prohibited unconditionally

## 5. Equivalence

Two canonical values are equal when, and only when:

- both are `number`, `percent`, or `currency` of the same kind with equal `num`
  and `den` (and, for `currency`, equal `symbol`); or
- both are `measurement` with equal rational value **and** identical canonical
  unit — no implicit unit conversion; or
- both are `time` with equal `minutes` and equal `meridiem`, where `null`
  meridiem equals only `null`; or
- both are `ratio` with equal reduced `terms`; or
- both are `quotrem` with equal `q` and `r`; or
- both are `text` with equal canonical strings.

Cross-kind comparison is never equal, with one exception: `number` and
`measurement` are compared as unequal *and* reported as `UNIT_ASSERTION` rather
than a plain mismatch, because that pair is the signature of the deleted
auto-fixer's behavior and must be visible in reports.

## 6. Mathematical rules

### 6.1 Fractions

- Answers are always in lowest terms. `gcd(num, den) != 1` → `FRACTION_NOT_LOWEST_TERMS`.
- `den == 1` must be written as an integer. `1/1`, `4/1` → `FRACTION_DENOMINATOR_ONE`.
- `den == 0` → `ZERO_DENOMINATOR`.
- Grades 1–4: `|num| > den` → `IMPROPER_FRACTION_FOR_GRADE`; the mixed-number form
  is required. Grades 5–12: improper fractions are permitted, because fraction
  operations that legitimately produce them (e.g. `3/4 ÷ 1/2 = 3/2`) begin there.
- These rules apply to distractors as well as to the answer. A `Fractions` item
  whose distractors are unreduced or improper is an `ERROR`, because it teaches
  the wrong normal form.

### 6.2 Decimals and rounding

- Exact comparison after normalization.
- A rounded answer is valid only when the stem states the rounding. An answer that
  differs from the exact solved value while the stem contains no rounding
  instruction → `UNROUNDED_WITHOUT_INSTRUCTION` (this is what catches
  `14.64 × 9.73 = 142.45`).
- Currency answers use at most 2 decimal places.

### 6.3 Units, signs, precision

- The answer's unit must equal the solver's unit by dimension, not by string:
  area → `cm2`/`m2`, volume → `cm3`/`m3`, length → `cm`/`m`/`km`/`mm`.
- `+ -`, `- -`, `+-` sequences in rendered question text → `MALFORMED_SIGN`.
- No unresolved placeholder (`___` outside a comparison stem, `TODO`, `TBD`,
  `undefined`, `NaN`, `null`, `Infinity`) → `PLACEHOLDER_TEXT`.

### 6.4 Division with remainder

- `0 <= r < divisor` for the answer **and** every distractor →
  `REMAINDER_GE_DIVISOR` otherwise.

### 6.5 Comparisons and orderings

- If the two operands of a `>`/`<`/`=` comparison are equal, the only correct
  answer is `=`; anything else → `EQUAL_OPERANDS_COMPARISON`.
- A "which is longer / larger / smaller" stem whose operands tie →
  `TIED_OPERANDS`.
- A "which is the largest/smallest" stem must have a unique extreme in the stem
  list (`TIED_EXTREME_IN_LIST`), and no choice may beat the stated answer
  (`DISTRACTOR_BEATS_ANSWER`).

### 6.6 Discounts and money

- `sale_price < original_price` is a parameter precondition →
  `SALE_PRICE_GE_ORIGINAL`.
- A "percent off" answer must be in `(0, 100)` → `NEGATIVE_PERCENT_OFF` /
  `PERCENT_OUT_OF_RANGE`.

### 6.7 Algebraic forms

Out of Phase 0 scope. An item whose answer is an algebraic expression is
`UNVERIFIED`, never `VALID`. String equality must not be used to accept it.

## 7. Structural gates

Applied to every question in every path (daily markdown, practice generator
output, curated pool entry). All are blocking.

| Code | Rule |
|---|---|
| `MISSING_FIELD` | required fields present and non-empty (question, choices, answer; French where the path requires it) |
| `CHOICE_COUNT` | exactly 4 choices for multiple choice |
| `DUPLICATE_CHOICES` | all 4 canonical choice values distinct |
| `CHOICE_IS_PREFIX_OF_CHOICE` | no choice's canonical text is a prefix of another's |
| `NO_CORRECT_OPTION` | exactly one choice equals the answer — zero is an error |
| `MULTIPLE_CORRECT_OPTIONS` | exactly one choice equals the answer — two or more is an error |
| `MULTIPLE_ANSWER_LINES` | at most one `Answer:` line per question |
| `SOLVER_DISAGREEMENT` | solver result equals the stated answer |
| `MISSING_FRENCH` | the French rendering is present where the path requires it |
| `DUPLICATE_RECENT_QUESTION` | no repeat of a normalized `(grade, question)` fingerprint within 30 days |
| `NONTERMINATING_GENERATION` | a generator must produce a question within a bounded step budget |

Two checks are reported but do not block, because they describe pedagogical quality
rather than mathematical or structural invalidity, and blocking on them would stop
publication for reasons unrelated to correctness:

- `HINT_LEAKS_ANSWER` — the hint or steps contain the answer value, or restate the
  stem's own numbers as the result.
- `POSITION_BIAS` — a run-level report: no option position should hold more than
  40% of correct answers across a publication run.

Both are surfaced in every report and counted in the phase status file. Promoting
either to blocking is an owner decision, not an implementation choice.

## 8. Bounded termination

Choice assembly must be total. Given a required choice count `n` and a distractor
generator, an implementation must either return `n` distinct canonical values
within a bounded number of attempts, or fail with `INSUFFICIENT_DISTRACTOR_SPACE`.
An unbounded retry loop is prohibited: the deleted fallback
`while (size < count) add(String(correct + size))` could never make progress when
the filler value was already present, which froze the browser tab. Every generator
therefore has a bounded-termination test.

## 9. Conformance fixtures

`conformance-fixtures.json`, next to this file, is the executable form of this
document. Sections:

- `parse` — surface form → canonical value, or `PARSE_FAILED`
- `equivalence` — pairs with the expected equality verdict and code
- `forbidden_fixes` — the 26 historically observed value-changing auto-fixer
  rewrites; each must be reported as an `ERROR` with the stated code and must
  never mutate content
- `questions` — whole-question cases with the expected verdict and codes

Both implementations run the same fixture file. A fixture may only be changed
together with this specification.
