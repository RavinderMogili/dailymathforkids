"""One-time repair: re-upsert every daily quiz to Supabase with correctly
aligned question/answer pairs.

Background: the old extraction used two independent regex scans for EN and
Answer lines. When the LLM wrote extra '- Answer:' lines inside Steps (or a
question had no Answer line), the answers array shifted — students were graded
against the wrong answers and Mistake History showed mismatched pairs.

Usage (PowerShell):
  $env:PUBLIC_API_BASE = "https://dailymathforkids-api.vercel.app"
  $env:SUPABASE_SERVICE_ROLE = "<service role key>"
  python scripts/repair_quizzes.py          # dry run — shows what would change
  python scripts/repair_quizzes.py --apply  # actually re-upserts
"""
import pathlib
import re
import sys

from gen_site import parse_grade_sections, extract_qa_pairs, upsert_quiz_to_supabase

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"


def main(apply=False):
    total, fixed = 0, 0
    for md_path in sorted(DAILY_DIR.glob("*.md")):
        day = md_path.stem
        text = md_path.read_text(encoding="utf-8")
        for code, content in parse_grade_sections(text).items():
            if not content.strip():
                continue
            total += 1
            old_qs = re.findall(r'^\s*-\s*EN:\s*(.+)', content, re.MULTILINE)
            old_ans = re.findall(r'^\s*-\s*Answer:\s*(.+?)(?:\s*$)', content, re.MULTILINE)
            qs, ans = extract_qa_pairs(content)
            was_broken = (len(old_qs) != len(old_ans)) or (old_ans != ans)
            if not was_broken:
                continue
            fixed += 1
            print(f"{'FIXING' if apply else 'WOULD FIX'}: {day}-{code} "
                  f"(old: {len(old_qs)}q/{len(old_ans)}a -> new: {len(qs)}q/{len(ans)}a)")
            if apply:
                upsert_quiz_to_supabase(f"{day}-{code}", qs, ans)
    print(f"\nDone. {fixed} of {total} quiz records {'re-upserted' if apply else 'need fixing'}.")
    if not apply and fixed:
        print("Run again with --apply to push the fixes to Supabase.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
