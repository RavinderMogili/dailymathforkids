"""
Full-dataset assessment pipeline for an external grade-school word-problem
dataset (GSM8K, OpenAI, MIT License — see tools/word-problems/ATTRIBUTION.md).

This script performs ONLY deterministic, reproducible, automated checks.
It does not call any AI model and does not claim to verify meaning or
pedagogical quality semantically — see ATTRIBUTION.md and the pilot report
for what still requires human/semantic review.

Usage:
  python tools/word-problems/assess.py --data-dir <path-to-grade_school_math/data> --out tools/word-problems/output

Reads the ORIGINAL question+answer files only:
  train.jsonl
  test.jsonl
(example_model_solutions.jsonl and *_socratic.jsonl are intentionally not
treated as additional source questions or as authoritative answers.)

For each record, produces:
  - a stable id (dataset + split + original line index)
  - cleaned "readable" solution steps (calculator annotations stripped)
  - independently recomputed / verified final numeric answer
  - heuristic grade estimate, difficulty, topic tag, reading-complexity score
  - suitability / ambiguity / duplicate flags
  - an automated review_status: "auto_ok", "needs_review", or "rejected"

review_status is NOT a claim of semantic correctness. "auto_ok" only means
the automated checks found no problem; every record still needs a human
pass before it can become "approved" for the app.
"""
import argparse
import hashlib
import json
import re
import sys
import ast
import operator as op
from collections import Counter
from pathlib import Path

# ── Safe arithmetic evaluation (no eval/exec on dataset text) ──────────────

_ALLOWED_BINOPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow,
}
_ALLOWED_UNARYOPS = {ast.UAdd: op.pos, ast.USub: op.neg}


class UnsafeExpression(Exception):
    pass


def safe_eval_arith(expr):
    """Evaluate a numeric expression containing only + - * / ( ) and numbers.
    Raises UnsafeExpression for anything else (names, calls, subscripts, etc.)."""
    node = ast.parse(expr, mode="eval").body
    return _eval_node(node)


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise UnsafeExpression(f"non-numeric constant: {node.value!r}")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand))
    raise UnsafeExpression(f"disallowed node: {type(node).__name__}")


CALC_ANNOTATION_RE = re.compile(r"<<([^=<>]+)=([^<>]+)>>")


def strip_calc_annotations(text):
    """Remove <<expr=value>> annotations, leaving natural kid-readable text.

    A handful of GSM8K answers have the annotation glued directly to the
    surrounding words with no space (e.g. "85 trees<<60+25=85>>on his farm"),
    which would merge into "85 treeson his farm" if simply deleted. Insert a
    single space in that case instead.
    """
    def repl(m):
        start, end = m.span()
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        if before.isalnum() and after.isalnum():
            return " "
        return ""
    cleaned = CALC_ANNOTATION_RE.sub(repl, text)
    return re.sub(r" {2,}", " ", cleaned)


def had_annotation_merge_risk(text):
    for m in CALC_ANNOTATION_RE.finditer(text):
        start, end = m.span()
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        if before.isalnum() and after.isalnum():
            return True
    return False


def verify_annotations(answer_text):
    """Check every <<expr=value>> annotation actually computes correctly.
    Returns (all_verified: bool, checked: int, mismatches: list[str])."""
    mismatches = []
    checked = 0
    last_value = None
    for m in CALC_ANNOTATION_RE.finditer(answer_text):
        expr, stated = m.group(1), m.group(2)
        checked += 1
        try:
            computed = safe_eval_arith(expr)
        except (UnsafeExpression, SyntaxError, ZeroDivisionError, ValueError) as e:
            mismatches.append(f"{expr}={stated} (eval error: {e})")
            continue
        try:
            stated_val = float(stated)
        except ValueError:
            mismatches.append(f"{expr}={stated} (non-numeric stated value)")
            continue
        if abs(computed - stated_val) > 1e-6 * max(1, abs(stated_val)):
            mismatches.append(f"{expr}={stated} (computed {computed})")
        last_value = stated_val
    return (len(mismatches) == 0, checked, mismatches, last_value)


FINAL_ANSWER_RE = re.compile(r"####\s*(-?[\d,]+(?:\.\d+)?)")


def extract_final_answer(answer_text):
    m = FINAL_ANSWER_RE.search(answer_text)
    if not m:
        return None
    return m.group(1).replace(",", "")


# ── Reading complexity (Flesch-Kincaid-style, no external libs) ────────────

VOWEL_GROUP_RE = re.compile(r"[aeiouyAEIOUY]+")


def estimate_syllables(word):
    word = re.sub(r"[^a-zA-Z]", "", word)
    if not word:
        return 0
    groups = VOWEL_GROUP_RE.findall(word)
    count = len(groups)
    if word.lower().endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def reading_complexity(text):
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = re.findall(r"[A-Za-z']+", text)
    n_sentences = max(len(sentences), 1)
    n_words = max(len(words), 1)
    n_syllables = sum(estimate_syllables(w) for w in words)
    grade_level = 0.39 * (n_words / n_sentences) + 11.8 * (n_syllables / n_words) - 15.59
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "est_syllables": n_syllables,
        "est_grade_level": round(grade_level, 1),
    }


# ── Topic / skill heuristics ────────────────────────────────────────────────

TOPIC_KEYWORDS = [
    ("Money", r"\$|dollar|cent|price|cost|paid|pay|spent|buy|bought|sell|sold|discount|change\b"),
    ("Time", r"\bhour|minute|second|day|week|month|year|clock|o'clock|morning|afternoon"),
    ("Percentages", r"percent|%"),
    ("Fractions", r"\bhalf\b|\bthird\b|\bquarter\b|\bfraction|\b\d+/\d+\b"),
    ("Ratios & Rates", r"\bper\b|\bratio\b|\brate\b|each\b.*costs|speed|mph|km/h"),
    ("Measurement", r"\bmeter|\bmetre|\bkilogram|\bgram\b|\bliter|\blitre|\binch|\bfoot|\bfeet|\byard|\bmile|\bcm\b|\bkg\b|\bml\b"),
    ("Geometry", r"\barea\b|\bperimeter\b|\bvolume\b|\btriangle\b|\brectangle\b|\bsquare\b|\bcircle\b"),
    ("Multiplication & Division", r"\beach\b|\bgroups? of\b|\bdivide|\bshare(d)? equally"),
    ("Counting & Comparison", r"\bmore than\b|\bfewer\b|\bless than\b|\baltogether\b|\bin total\b|\bcombined\b"),
]
TOPIC_PATTERNS = [(name, re.compile(pat, re.I)) for name, pat in TOPIC_KEYWORDS]


def classify_topic(question):
    for name, pattern in TOPIC_PATTERNS:
        if pattern.search(question):
            return name
    return "Word Problems (general)"


# ── Suitability screening (automated, conservative) ────────────────────────

SUITABILITY_KEYWORDS = re.compile(
    r"\b(gun|guns|shoot|shot|kill|killed|killing|murder|suicide|drug|drugs|cocaine|"
    r"heroin|marijuana|weed\b|cigarette|cigarettes|smoking|tobacco|vape|vaping|"
    r"beer|wine|vodka|whiskey|alcohol|drunk|gambl|casino|bet\b|bets\b|betting|"
    r"lottery|poker|blood|wound|stab|knife|weapon|abuse|rape|sex\b|sexual|"
    r"pregnant|pregnancy|divorce|affair|prison|jail|arrested|steal(?:s|ing)?\b|theft|"
    r"robbed|robbery|debt\b|bankrupt|war\b|bomb|terroris|racist|racism)\b",
    re.I,
)


def screen_suitability(question):
    hits = sorted(set(m.group(0).lower() for m in SUITABILITY_KEYWORDS.finditer(question)))
    return hits


# ── Ambiguity checks ────────────────────────────────────────────────────────

UNIT_WORDS = ["cm", "meter", "metre", "km", "kilometer", "mm", "inch", "foot", "feet",
              "yard", "mile", "kg", "gram", "pound", "lb", "liter", "litre", "ml", "gallon"]


def check_unit_ambiguity(question):
    found = set()
    for u in UNIT_WORDS:
        if re.search(r"\b" + re.escape(u) + r"s?\b", question, re.I):
            # normalize to a rough unit family for a light mixed-system check
            if u in ("cm", "meter", "metre", "km", "kilometer", "mm"):
                found.add("metric-length")
            elif u in ("inch", "foot", "feet", "yard", "mile"):
                found.add("imperial-length")
            elif u in ("kg", "gram", "pound", "lb"):
                found.add("mass")
            elif u in ("liter", "litre", "ml", "gallon"):
                found.add("volume")
    return len(set(f.split("-")[0] for f in found if "-" in f)) + (
        1 if "imperial-length" in found and "metric-length" in found else 0
    ) > 1 and ("imperial-length" in found and "metric-length" in found)


ROUNDING_WORDS_RE = re.compile(r"\babout\b|\bapproximately\b|\baround\b|\broughly\b", re.I)


def check_rounding_language(question):
    return bool(ROUNDING_WORDS_RE.search(question))


NON_INTEGER_COUNT_NOUNS = re.compile(
    r"\b(people|person|student|students|child|children|kid|kids|friend|friends|"
    r"dog|dogs|cat|cats|animal|animals|car|cars|book|books|apple|apples|egg|eggs|"
    r"ticket|tickets|toy|toys|chair|chairs|table|tables|pencil|pencils)\b", re.I
)


def check_unrealistic_fraction(question, final_answer):
    if final_answer is None:
        return False
    try:
        val = float(final_answer)
    except ValueError:
        return False
    if val == int(val):
        return False
    return bool(NON_INTEGER_COUNT_NOUNS.search(question))


# ── Duplicate detection (exact + template near-duplicate) ─────────────────

STOPWORDS = set("a an the of to in on for and or is are was were how many much "
                 "does do did has have had he she it they them his her their".split())
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def normalize_exact(text):
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def normalize_template(text):
    """Normalize for near-duplicate detection: numbers -> '#', drop stopwords."""
    t = NUMBER_RE.sub("#", text.lower())
    t = re.sub(r"[^a-z#\s]", "", t)
    tokens = [w for w in t.split() if w not in STOPWORDS]
    return tokens


def shingles(tokens, n=3):
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def blocking_key(tokens):
    """Cheap block key so we only compare within same-ish problems, not all-pairs."""
    significant = sorted(set(t for t in tokens if len(t) > 3))[:3]
    return (len(tokens) // 5, tuple(significant))


# ── Main pipeline ────────────────────────────────────────────────────────

def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            records.append((i, json.loads(line)))
    return records


def _word_set(text):
    return set(re.findall(r"[a-z']+", text.lower()))


def is_question_echo(step_line, question):
    """Some GSM8K answers accidentally repeat the question verbatim as a
    trailing 'step' with no calculation — not a real explanation step."""
    a, b = _word_set(step_line), _word_set(question)
    if not a or not b:
        return False
    overlap = len(a & b) / len(a | b)
    return overlap >= 0.75


def assess_record(rec_id, split, index, question, answer_text):
    verified, checked, mismatches, last_annotation_val = verify_annotations(answer_text)
    final_answer = extract_final_answer(answer_text)
    final_matches_last = (
        last_annotation_val is not None and final_answer is not None and
        abs(last_annotation_val - float(final_answer)) < 1e-6 * max(1, abs(float(final_answer)))
    )
    arithmetic_verified = verified and (final_matches_last or checked == 0) and final_answer is not None

    readable_steps = [s.strip() for s in strip_calc_annotations(answer_text).split("\n")
                       if s.strip() and not s.strip().startswith("####")]
    question_echo_removed = False
    if readable_steps and is_question_echo(readable_steps[-1], question):
        readable_steps = readable_steps[:-1]
        question_echo_removed = True
    annotation_merge_fixed = had_annotation_merge_risk(answer_text)

    complexity = reading_complexity(question)
    topic = classify_topic(question)
    suitability_hits = screen_suitability(question + " " + answer_text)
    unit_ambiguous = check_unit_ambiguity(question)
    rounding_lang = check_rounding_language(question)
    unrealistic_fraction = check_unrealistic_fraction(question, final_answer)

    n_steps = max(len(readable_steps), 1)
    grade_level = complexity["est_grade_level"]
    has_pct_frac = bool(re.search(r"percent|%|\b\d+/\d+\b", question, re.I))
    has_decimal = bool(re.search(r"\$?\d+\.\d+", question))

    # Provisional difficulty from step count (documented heuristic, not curriculum-verified)
    if n_steps <= 2:
        difficulty = "easy"
    elif n_steps <= 4:
        difficulty = "medium"
    else:
        difficulty = "hard"

    # Provisional grade estimate — heuristic only, NOT a curriculum mapping.
    score = n_steps + (2 if has_pct_frac else 0) + (1 if has_decimal else 0) + max(0, (grade_level - 3) / 2)
    grade_estimate = min(12, max(2, round(2 + score)))

    return {
        "id": rec_id,
        "source": {"dataset": "GSM8K", "split": split, "index": index},
        "original": {"question": question, "answer": answer_text},
        "final_answer": final_answer,
        "readable_steps": readable_steps,
        "arithmetic": {
            "annotations_checked": checked,
            "annotations_verified": verified,
            "mismatches": mismatches,
            "final_matches_last_annotation": final_matches_last,
            "arithmetic_verified": arithmetic_verified,
        },
        "topic": topic,
        "difficulty": difficulty,
        "grade_estimate": grade_estimate,
        "reading_complexity": complexity,
        "flags": {
            "suitability_hits": suitability_hits,
            "unit_ambiguous": unit_ambiguous,
            "rounding_language": rounding_lang,
            "unrealistic_fraction_count": unrealistic_fraction,
            "annotation_merge_fixed": annotation_merge_fixed,
            "question_echo_removed": question_echo_removed,
            "no_explanation_steps": len(readable_steps) == 0,
        },
        "_exact_key": normalize_exact(question),
        "_template_tokens": normalize_template(question),
    }


def find_duplicates(records):
    exact_seen = {}
    blocks = {}
    for r in records:
        key = r["_exact_key"]
        if key in exact_seen:
            r["flags"]["exact_duplicate_of"] = exact_seen[key]
        else:
            exact_seen[key] = r["id"]
            r["flags"]["exact_duplicate_of"] = None
        bkey = blocking_key(r["_template_tokens"])
        blocks.setdefault(bkey, []).append(r)

    for bucket in blocks.values():
        if len(bucket) < 2:
            for r in bucket:
                r["flags"].setdefault("near_duplicate_of", None)
            continue
        shingle_cache = {r["id"]: shingles(r["_template_tokens"]) for r in bucket}
        for r in bucket:
            r["flags"].setdefault("near_duplicate_of", None)
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                a, b = bucket[i], bucket[j]
                if a["flags"]["near_duplicate_of"] or b["flags"]["exact_duplicate_of"]:
                    continue
                sim = jaccard(shingle_cache[a["id"]], shingle_cache[b["id"]])
                if sim >= 0.8 and b["flags"]["near_duplicate_of"] is None:
                    b["flags"]["near_duplicate_of"] = a["id"]


def decide_status(r):
    f = r["flags"]
    if f["suitability_hits"]:
        return "rejected", "suitability keyword hit: " + ", ".join(f["suitability_hits"])
    if not r["arithmetic"]["arithmetic_verified"]:
        return "rejected", "arithmetic could not be automatically verified"
    if r["final_answer"] is None:
        return "rejected", "no parseable final answer"
    if f["no_explanation_steps"]:
        return "rejected", "no explanation steps could be extracted"
    if f.get("exact_duplicate_of"):
        return "rejected", f"exact duplicate of {f['exact_duplicate_of']}"
    reasons = []
    if f.get("near_duplicate_of"):
        reasons.append(f"near-duplicate of {f['near_duplicate_of']}")
    if f["unit_ambiguous"]:
        reasons.append("mixed measurement units")
    if f["rounding_language"]:
        reasons.append("uses approximate/rounding language")
    if f["unrealistic_fraction_count"]:
        reasons.append("non-integer answer for a discrete-count question")
    if reasons:
        return "needs_review", "; ".join(reasons)
    return "auto_ok", "passed all automated checks (still needs human/semantic review before approval)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="path to grade_school_math/data")
    ap.add_argument("--out", default="tools/word-problems/output")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_records = []
    split_counts = {}
    for split, filename in (("train", "train.jsonl"), ("test", "test.jsonl")):
        path = data_dir / filename
        if not path.exists():
            print(f"ERROR: missing {path}", file=sys.stderr)
            sys.exit(1)
        raw = load_jsonl(path)
        split_counts[split] = len(raw)
        for index, obj in raw:
            rec_id = f"gsm8k-{split}-{index:05d}"
            all_records.append(assess_record(rec_id, split, index, obj["question"], obj["answer"]))

    find_duplicates(all_records)
    for r in all_records:
        status, reason = decide_status(r)
        r["review_status"] = status
        r["review_reason"] = reason
        del r["_exact_key"]
        del r["_template_tokens"]

    # Write full per-record output (kept local/gitignored — see README)
    full_path = out_dir / "assessed_records.jsonl"
    with open(full_path, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    status_counts = Counter(r["review_status"] for r in all_records)
    grade_counts = Counter(r["grade_estimate"] for r in all_records)
    difficulty_counts = Counter(r["difficulty"] for r in all_records)
    topic_counts = Counter(r["topic"] for r in all_records)
    arithmetic_ok = sum(1 for r in all_records if r["arithmetic"]["arithmetic_verified"])
    suitability_rejected = sum(1 for r in all_records if r["flags"]["suitability_hits"])
    exact_dupes = sum(1 for r in all_records if r["flags"]["exact_duplicate_of"])
    near_dupes = sum(1 for r in all_records if r["flags"].get("near_duplicate_of"))
    merge_fixed = sum(1 for r in all_records if r["flags"]["annotation_merge_fixed"])

    report = {
        "dataset": "GSM8K (OpenAI, MIT License)",
        "source_files": ["train.jsonl", "test.jsonl"],
        "records_per_split": split_counts,
        "total_records_parsed": len(all_records),
        "automated_checks": {
            "arithmetic_independently_verified": arithmetic_ok,
            "arithmetic_verification_failed": len(all_records) - arithmetic_ok,
            "suitability_keyword_hits": suitability_rejected,
            "exact_duplicates": exact_dupes,
            "near_duplicates_flagged": near_dupes,
            "missing_space_auto_fixed": merge_fixed,
        },
        "review_status_counts": dict(status_counts),
        "grade_estimate_distribution": dict(sorted(grade_counts.items())),
        "difficulty_distribution": dict(difficulty_counts),
        "topic_distribution": dict(topic_counts.most_common()),
        "notes": [
            "grade_estimate and topic are heuristic/automated only — not a curriculum mapping "
            "and not semantically reviewed. Treat as provisional.",
            "review_status='auto_ok' means automated checks passed only; it is NOT a claim that "
            "the question was read and judged suitable by a human/teacher OR by an AI/LLM. A "
            "separate, smaller subset went through AI semantic review (an LLM read each one) — "
            "see tools/word-problems/output/pilot_shortlist.json and README.md 'Three distinct "
            "review tiers.' No record in this dataset has had human/teacher review.",
            "example_model_solutions.jsonl and the Socratic variants were not used as source "
            "questions or as authoritative answers, per project instructions.",
        ],
    }
    with open(out_dir / "assessment_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\nFull per-record output: {full_path}")


if __name__ == "__main__":
    main()
