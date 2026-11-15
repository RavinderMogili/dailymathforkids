"""
Expands data/practice-pool-extended.json with additional vetted GSM8K
candidates from candidates.jsonl, without touching the existing 500.

Uses the same topic-cap balancing as pick_pilot.py (MAX_SHARE_PER_TOPIC),
applied only to candidates not already in the approved pool, so the
existing pool — including manually reviewed items — stays untouched.

Usage:
  python tools/word-problems/expand_pool.py --target 300
"""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / "tools/word-problems/output/candidates.jsonl"
POOL = ROOT / "data/practice-pool-extended.json"

random.seed(20261115)

# Extra questions per grade — keeps the existing G4-5-heavy skew.
GRADE_TARGETS = {4: 96, 5: 102, 6: 60, 7: 42}
MAX_SHARE_PER_TOPIC = 0.4


def scale_targets(target):
    base_total = sum(GRADE_TARGETS.values())
    scaled = {g: (t * target) // base_total for g, t in GRADE_TARGETS.items()}
    remainder = target - sum(scaled.values())
    if remainder:
        biggest_grade = max(GRADE_TARGETS, key=GRADE_TARGETS.get)
        scaled[biggest_grade] += remainder
    return scaled


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


def pick_balanced(recs, target):
    """Round-robin across topics with a per-topic cap — mirrors pick_pilot.py."""
    by_topic = defaultdict(list)
    random.shuffle(recs)
    for rec in recs:
        by_topic[rec["topic"]].append(rec)
    cap = max(1, int(target * MAX_SHARE_PER_TOPIC))
    taken_by_topic = defaultdict(int)
    chosen = []
    topics = list(by_topic.keys())
    idx = 0
    while len(chosen) < target and any(by_topic[t] for t in topics):
        t = topics[idx % len(topics)]
        idx += 1
        if by_topic[t] and taken_by_topic[t] < cap:
            chosen.append(by_topic[t].pop())
            taken_by_topic[t] += 1
        if idx > target * 20:
            break
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=300,
                    help="Number of additional questions to add")
    args = ap.parse_args()

    pool = json.loads(POOL.read_text(encoding="utf-8"))
    used = {r["_sourceId"] for r in pool}

    by_grade = defaultdict(list)
    for line in CANDIDATES.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["id"] not in used:
            by_grade[rec["grade_estimate"]].append(rec)

    added = []
    for grade, target in scale_targets(args.target).items():
        chosen = pick_balanced(by_grade.get(grade, []), target)
        if len(chosen) < target:
            print(f"WARN: grade {grade} only had {len(chosen)} unused "
                  f"candidates (wanted {target})")
        added.extend(chosen)

    pool.extend(to_runtime_shape(r) for r in added)
    POOL.write_text(json.dumps(pool, indent=2, ensure_ascii=False),
                    encoding="utf-8")

    by_grade_count = defaultdict(int)
    for r in added:
        by_grade_count[r["grade_estimate"]] += 1
    print(f"Added {len(added)} -> {POOL} (total now {len(pool)})")
    print("Added by grade:", dict(sorted(by_grade_count.items())))


if __name__ == "__main__":
    main()
