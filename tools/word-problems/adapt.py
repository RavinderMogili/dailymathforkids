"""
Adapts assessed source-dataset records (see assess.py) into the app's
multiple-choice practice-question format, with plausible wrong-answer
distractors and a mathematical-equivalence check so no two choices can
accidentally both be "correct" (e.g. 0.5 / 1/2 / 2/4).

This performs NO semantic verification — it only re-checks arithmetic and
generates distractors. Every record it outputs is status
"candidate_ready_for_review": a human still has to read it before it can be
marked "approved" and imported into the app (see import_pool.py and
tools/word-problems/README.md).

Usage:
  python tools/word-problems/adapt.py \
      --in tools/word-problems/output/assessed_records.jsonl \
      --out tools/word-problems/output/candidates.jsonl \
      --grades 4 5 6 7 \
      --max-per-grade 400
"""
import argparse
import json
import random
import re
from collections import defaultdict
from fractions import Fraction

random.seed(20260905)  # deterministic distractor generation for reproducibility

CALC_RE = re.compile(r"<<([^=<>]+)=([^<>]+)>>")


def parse_number(s):
    try:
        return Fraction(s)
    except (ValueError, ZeroDivisionError):
        try:
            return Fraction(str(float(s)))
        except ValueError:
            return None


def fmt_number(frac):
    if frac.denominator == 1:
        return str(frac.numerator)
    val = float(frac)
    # Render as a clean decimal (GSM8K final answers are always plain numbers)
    if abs(val - round(val, 2)) < 1e-9:
        return f"{val:.2f}".rstrip("0").rstrip(".")
    return str(val)


def extract_calc_values(answer_text):
    """Return list of (expr, stated_value_as_Fraction) in order of appearance."""
    out = []
    for m in CALC_RE.finditer(answer_text):
        val = parse_number(m.group(2))
        if val is not None:
            out.append((m.group(1), val))
    return out


def gen_distractors(correct, calc_values, n=3):
    """Generate up to n plausible wrong answers based on common mistake patterns."""
    is_whole = correct.denominator == 1
    candidates = []

    # 1. Stopped one step early (common mistake): the second-to-last computed value.
    #    Only plausible as a *final*-answer mistake if it's roughly the same order of
    #    magnitude as the real answer — an intermediate rate/percentage (e.g. 0.1) is
    #    not a believable final answer for a $220,000 question.
    if len(calc_values) >= 2:
        candidates.append(calc_values[-2][1])

    # 2. Flipped the final operation (+ <-> -, * <-> /) on the final step's operands,
    #    when the final expr is a simple "a OP b" form.
    if calc_values:
        last_expr = calc_values[-1][0]
        m = re.match(r"^\s*([\d.]+)\s*([+\-*/])\s*([\d.]+)\s*$", last_expr)
        if m:
            a, sign, b = Fraction(m.group(1)), m.group(2), Fraction(m.group(3))
            flipped = {"+": "-", "-": "+", "*": "/", "/": "*"}[sign]
            try:
                if flipped == "+":
                    candidates.append(a + b)
                elif flipped == "-":
                    candidates.append(a - b)
                elif flipped == "*":
                    candidates.append(a * b)
                elif flipped == "/" and b != 0:
                    candidates.append(a / b)
            except ZeroDivisionError:
                pass

    # 3. Scaled perturbations (bounded, plausible-looking). Several deltas so that
    #    if some get filtered out below (off-scale, negative, duplicate) there are
    #    still enough left to reach n.
    for factor in (Fraction(1, 2), Fraction(2, 1), Fraction(3, 4), Fraction(5, 4)):
        candidates.append(correct * factor)
    for pct in (Fraction(1, 10), Fraction(1, 5), Fraction(3, 10)):
        delta = max(Fraction(1, 1), abs(correct) * pct)
        candidates.append(correct + delta)
        candidates.append(correct - delta)

    # If the real answer is a whole number, a wrong choice with a fractional part is
    # an instant giveaway ("66" vs "72.6" — nobody would pick the decimal one) — round.
    if is_whole:
        candidates = [Fraction(round(c)) for c in candidates]

    # Plausibility bound: reject anything wildly off-scale from the correct answer
    # (e.g. picking up an intermediate percentage/rate like 0.1 as a "final answer"
    # distractor next to 220000). Keeps distractors in the same ballpark as a real
    # student mistake would be.
    lo, hi = abs(correct) * Fraction(1, 20), abs(correct) * 20
    if correct == 0:
        lo, hi = Fraction(-5), Fraction(5)

    # Dedup by numeric value (this IS the equivalence check: 0.5 == 1/2 == 2/4)
    seen = {correct}
    unique = []
    for c in candidates:
        if c is None or c in seen:
            continue
        if c < 0 and correct >= 0:
            continue
        if correct != 0 and not (lo <= abs(c) <= hi):
            continue
        seen.add(c)
        unique.append(c)

    random.shuffle(unique)
    return unique[:n]


TOPIC_HINTS = {
    "Money": "Work out each amount step by step, then add or subtract like you would with regular numbers — just remember the $ sign.",
    "Time": "Break it into smaller time chunks (hours, then minutes) and work through them one at a time.",
    "Percentages": 'Remember: percent means "out of 100." Turn the percent into a fraction or decimal first.',
    "Fractions": "Find a common step: what is half, a third, or a quarter of the number first?",
    "Ratios & Rates": "Figure out the rate for ONE item or ONE unit first, then multiply for the amount you need.",
    "Measurement": "Check what unit the question wants, and convert if needed before doing the math.",
    "Geometry": "Picture the shape and think about which formula (perimeter, area, etc.) fits.",
    "Multiplication & Division": "Think about equal groups: how many groups, and how many in each group?",
    "Counting & Comparison": "Read carefully to see if you need to add, subtract, or compare the amounts.",
    "Word Problems (general)": "Read the problem twice. Underline the numbers and figure out what question is being asked.",
}


def adapt_record(rec):
    final = parse_number(rec["final_answer"])
    if final is None:
        return None, "final answer not numeric"
    calc_values = extract_calc_values(rec["original"]["answer"])
    distractors = gen_distractors(final, calc_values, n=3)
    if len(distractors) < 3:
        return None, f"could not generate 3 unique distractors (got {len(distractors)})"

    choices = [fmt_number(final)] + [fmt_number(d) for d in distractors]
    # Final safety net: re-verify exactly one choice is numerically equal to the answer
    numeric_choices = [parse_number(c) for c in choices]
    if numeric_choices.count(final) != 1 or len(set(numeric_choices)) != 4:
        return None, "distractor equivalence check failed"

    random.shuffle(choices)

    # Cap at 4 steps for a child-friendly explanation, but always keep the LAST
    # step — it's the one that actually states how the final answer was reached.
    all_steps = rec["readable_steps"]
    if len(all_steps) <= 4:
        steps = all_steps
    else:
        steps = all_steps[:3] + [all_steps[-1]]
    candidate = {
        "id": rec["id"],
        "source": {
            "dataset": "GSM8K",
            "split": rec["source"]["split"],
            "index": rec["source"]["index"],
            "license": "MIT",
            "attribution": "OpenAI, Cobbe et al. 2021 (github.com/openai/grade-school-math)",
        },
        "original": {"question": rec["original"]["question"], "answer": rec["original"]["answer"]},
        "adapted_question": None,  # set to a string if wording is changed during manual review
        "grade_estimate": rec["grade_estimate"],
        "topic": rec["topic"],
        "skill_tags": [rec["topic"]],
        "difficulty": rec["difficulty"],
        "question": rec["original"]["question"],
        "questionFr": "",
        "choices": choices,
        "answer": fmt_number(final),
        "hint": TOPIC_HINTS.get(rec["topic"], TOPIC_HINTS["Word Problems (general)"]),
        "steps": steps,
        "validation": {
            "arithmetic_verified": rec["arithmetic"]["arithmetic_verified"],
            "distractors_mathematically_distinct": True,
            "automated_flags": rec["flags"],
        },
        "review_status": "candidate_ready_for_review",
    }
    return candidate, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    ap.add_argument("--grades", nargs="+", type=int, default=[4, 5, 6, 7])
    ap.add_argument("--max-per-grade", type=int, default=500)
    args = ap.parse_args()

    per_grade = defaultdict(int)
    written = 0
    skipped_reasons = defaultdict(int)

    with open(args.infile, encoding="utf-8") as fin, open(args.outfile, "w", encoding="utf-8") as fout:
        for line in fin:
            rec = json.loads(line)
            if rec["review_status"] != "auto_ok":
                continue
            if rec["grade_estimate"] not in args.grades:
                continue
            if per_grade[rec["grade_estimate"]] >= args.max_per_grade:
                continue
            candidate, err = adapt_record(rec)
            if candidate is None:
                skipped_reasons[err] += 1
                continue
            fout.write(json.dumps(candidate, ensure_ascii=False) + "\n")
            per_grade[rec["grade_estimate"]] += 1
            written += 1

    print(f"Wrote {written} candidates to {args.outfile}")
    print("Per grade:", dict(per_grade))
    if skipped_reasons:
        print("Skipped (adaptation failed):", dict(skipped_reasons))


if __name__ == "__main__":
    main()
