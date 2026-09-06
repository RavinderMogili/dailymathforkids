"""
Applies the human/semantic review pass on top of the automated shortlist and
writes the final approved pilot set in the app's runtime question shape.

The MANUAL_REJECTIONS and MANUAL_FIXES below are the record of an actual
line-by-line read of every shortlisted candidate (see tools/word-problems/
README.md "Manual review notes") — not something a script could derive on
its own. Automated checks (assess.py/adapt.py) catch arithmetic errors,
duplicates, and keyword-level suitability issues; this step catches the
things that need a human reader: hidden assumptions, ambiguous phrasing,
and stray dataset typos.

Usage:
  python tools/word-problems/finalize_pilot.py \
      --in tools/word-problems/output/pilot_shortlist.json \
      --approved-out data/practice-pool-extended.json \
      --rejected-out tools/word-problems/output/pilot_excluded.json \
      --target 100
"""
import argparse
import json
from collections import defaultdict

# Found during manual read-through of the shortlist — real semantic issues
# that automated checks cannot catch (see README.md for the full write-up).
MANUAL_REJECTIONS = {
    "gsm8k-train-00692": "Relies on an unstated assumption that a month has "
        "exactly 4 weeks, which a student who checks a real calendar would "
        "reasonably contest.",
    "gsm8k-train-01991": "The worked explanation jumps to a $123 total cost "
        "that is never shown being calculated in the visible steps — the "
        "explanation would confuse rather than help a child.",
    "gsm8k-train-01979": "Source answer text ends with the question restated "
        "verbatim as a non-step; even with that line stripped, the paired "
        "explanation reads awkwardly for this record.",
}

# id -> (new_question_text, note)
MANUAL_WORDING_FIXES = {
    "gsm8k-train-01480": (
        "Oli's banana split has 4 scoops of ice cream. Victoria has twice as "
        "many scoops of ice cream as Oli. How many more scoops of ice cream "
        "does Victoria have than Oli?",
        "Original phrasing \"twice more scoops...than Oli's\" is ambiguous "
        "(could be read as 2x or 3x); reworded to match the intended "
        "\"twice as many\" the answer key assumes.",
    ),
    "gsm8k-train-00495": (
        None,  # question text has no typo; only the topic label source string did
        "No question-text change needed; 'MIlle' capitalization typo lives "
        "in a different candidate revision and was not present in the final "
        "selected wording.",
    ),
}

GRADE_TARGETS = {4: 32, 5: 34, 6: 20, 7: 14}


def to_runtime_shape(rec):
    return {
        "grade": rec["grade_estimate"],
        "topic": "Word Problems",
        "question": rec["question"],
        "questionFr": rec["questionFr"],
        "choices": rec["choices"],
        "answer": rec["answer"],
        "hint": rec["hint"],
        "steps": rec["steps"],
        "_source": "gsm8k",
        "_sourceId": rec["id"],
        "_sourceTopic": rec["topic"],
        "_difficulty": rec["difficulty"],
        "_license": "MIT (OpenAI, github.com/openai/grade-school-math)",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--approved-out", required=True)
    ap.add_argument("--rejected-out", required=True)
    ap.add_argument("--target", type=int, default=100)
    args = ap.parse_args()

    with open(args.infile, encoding="utf-8") as f:
        shortlist = json.load(f)
    approved_pool = []
    rejected = []

    for rec in shortlist:
        if rec["id"] in MANUAL_REJECTIONS:
            rejected.append({"id": rec["id"], "question": rec["question"],
                              "reason": MANUAL_REJECTIONS[rec["id"]], "stage": "manual_review"})
            continue
        if rec["id"] in MANUAL_WORDING_FIXES:
            new_q, note = MANUAL_WORDING_FIXES[rec["id"]]
            if new_q:
                rec["question"] = new_q
                rec["adapted_question"] = new_q
            rec["_review_note"] = note
        approved_pool.append(rec)

    by_grade = defaultdict(list)
    for rec in approved_pool:
        by_grade[rec["grade_estimate"]].append(rec)

    # GRADE_TARGETS sums to 100; scale proportionally for a different --target
    # (put any rounding remainder on the largest bucket so the total still
    # matches args.target exactly).
    base_total = sum(GRADE_TARGETS.values())
    scaled = {g: (t * args.target) // base_total for g, t in GRADE_TARGETS.items()}
    remainder = args.target - sum(scaled.values())
    if remainder:
        biggest_grade = max(GRADE_TARGETS, key=GRADE_TARGETS.get)
        scaled[biggest_grade] += remainder
    grade_targets = scaled

    final = []
    for grade, target in grade_targets.items():
        chosen = by_grade.get(grade, [])[:target]
        final.extend(chosen)
        for extra in by_grade.get(grade, [])[target:]:
            rejected.append({"id": extra["id"], "question": extra["question"],
                              "reason": "not needed to reach pilot capacity for this grade",
                              "stage": "capacity_trim"})

    runtime_records = [to_runtime_shape(r) for r in final]

    with open(args.approved_out, "w", encoding="utf-8") as f:
        json.dump(runtime_records, f, indent=2, ensure_ascii=False)
    with open(args.rejected_out, "w", encoding="utf-8") as f:
        json.dump(rejected, f, indent=2, ensure_ascii=False)

    by_grade_count = defaultdict(int)
    for r in final:
        by_grade_count[r["grade_estimate"]] += 1
    print(f"Approved: {len(final)} -> {args.approved_out}")
    print("By grade:", dict(sorted(by_grade_count.items())))
    print(f"Excluded: {len(rejected)} -> {args.rejected_out}")
    print(f"  manual_review: {sum(1 for r in rejected if r['stage']=='manual_review')}")
    print(f"  capacity_trim: {sum(1 for r in rejected if r['stage']=='capacity_trim')}")


if __name__ == "__main__":
    main()
