"""
Selects a diverse, grade/topic-balanced pilot subset from candidates.jsonl
for AI semantic review (an LLM reading each one — see README.md "Three
distinct review tiers"; this is NOT human/teacher review). This is a
*shortlist* step only — every record it outputs still gets read (by an AI
reviewer, in this pipeline's actual usage) before approval.

Usage:
  python tools/word-problems/pick_pilot.py \
      --in tools/word-problems/output/candidates.jsonl \
      --out tools/word-problems/output/pilot_shortlist.json \
      --target 130
"""
import argparse
import json
import random
from collections import defaultdict

random.seed(20260905)

# Priority skews toward Grades 1-5 per project brief; GSM8K has essentially no
# content that reads at a true Grade 1-3 level (see assessment_report.json),
# so the pilot is weighted to grades 4-5 with a smaller stretch into 6-7.
GRADE_TARGETS = {4: 42, 5: 44, 6: 26, 7: 18}
MAX_SHARE_PER_TOPIC = 0.4  # no single topic should dominate a grade's slice


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True)
    ap.add_argument("--out", dest="outfile", required=True)
    args = ap.parse_args()

    by_grade = defaultdict(list)
    with open(args.infile, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            by_grade[rec["grade_estimate"]].append(rec)

    selected = []
    for grade, target in GRADE_TARGETS.items():
        pool = by_grade.get(grade, [])
        random.shuffle(pool)
        by_topic = defaultdict(list)
        for rec in pool:
            by_topic[rec["topic"]].append(rec)
        cap = max(1, int(target * MAX_SHARE_PER_TOPIC))
        taken_by_topic = defaultdict(int)
        chosen = []
        # Round-robin across topics so no single topic dominates
        topics = list(by_topic.keys())
        idx = 0
        while len(chosen) < target and any(by_topic[t] for t in topics):
            t = topics[idx % len(topics)]
            idx += 1
            if by_topic[t] and taken_by_topic[t] < cap:
                chosen.append(by_topic[t].pop())
                taken_by_topic[t] += 1
            if idx > target * 20:  # safety valve
                break
        selected.extend(chosen)

    with open(args.outfile, "w", encoding="utf-8") as f:
        json.dump(selected, f, indent=2, ensure_ascii=False)

    by_grade_count = defaultdict(int)
    by_topic_count = defaultdict(int)
    for r in selected:
        by_grade_count[r["grade_estimate"]] += 1
        by_topic_count[r["topic"]] += 1
    print(f"Selected {len(selected)} shortlist candidates -> {args.outfile}")
    print("By grade:", dict(sorted(by_grade_count.items())))
    print("By topic:", dict(by_topic_count))


if __name__ == "__main__":
    main()
