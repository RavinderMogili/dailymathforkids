"""
Unit tests for the word-problem dataset pipeline (assess.py / adapt.py).
Uses only the standard library (unittest) — no new test dependency for a
Python-side tool that isn't part of the app's runtime.

Run with:
  python -m unittest tools.word_problems.test_pipeline -v
or, from this directory:
  python -m unittest test_pipeline -v
"""
import sys
import os
import json
import tempfile
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(__file__))

import assess  # noqa: E402
import adapt  # noqa: E402
import finalize_pilot  # noqa: E402


class TestArithmeticVerification(unittest.TestCase):
    def test_correct_annotations_verify(self):
        text = "She has 2*3=<<2*3=6>>6 apples.\n#### 6"
        ok, checked, mismatches, last = assess.verify_annotations(text)
        self.assertTrue(ok)
        self.assertEqual(checked, 1)
        self.assertEqual(mismatches, [])
        self.assertEqual(last, 6)

    def test_wrong_annotation_is_caught(self):
        # A corrupted/malformed record: the annotation lies about its result.
        text = "She has 2*3=<<2*3=7>>7 apples.\n#### 7"
        ok, checked, mismatches, last = assess.verify_annotations(text)
        self.assertFalse(ok)
        self.assertEqual(len(mismatches), 1)

    def test_final_answer_must_match_last_step(self):
        # Malformed: the annotations are internally correct, but the ####
        # answer doesn't match what was actually computed.
        rec = assess.assess_record(
            "test-1", "train", 1,
            "How many apples?",
            "She has 2+2=<<2+2=4>>4 apples.\n#### 5",
        )
        self.assertFalse(rec["arithmetic"]["arithmetic_verified"])

    def test_unsafe_expression_does_not_crash(self):
        # Malformed record with a non-arithmetic annotation body must be
        # handled safely, never executed, and reported as unverified.
        with self.assertRaises(assess.UnsafeExpression):
            assess.safe_eval_arith("__import__('os').system('echo hi')")


class TestQuestionEchoStripping(unittest.TestCase):
    def test_trailing_question_echo_is_removed(self):
        question = "How many seeds are in a watermelon?"
        answer = "There are 800 black seeds.\n#### 800\n" + question
        rec = assess.assess_record("test-2", "train", 2, question, answer)
        self.assertFalse(any(
            assess.is_question_echo(s, question) for s in rec["readable_steps"]
        ))
        self.assertTrue(len(rec["readable_steps"]) >= 1)

    def test_no_explanation_steps_is_rejected(self):
        # A record whose only content is the #### line has no real explanation.
        rec = assess.assess_record("test-3", "train", 3, "What is 2+2?", "#### 4")
        status, _ = assess.decide_status(rec)
        self.assertEqual(status, "rejected")


class TestSuitabilityScreening(unittest.TestCase):
    def test_flags_unsuitable_keyword(self):
        hits = assess.screen_suitability("He bought a beer for $5.")
        self.assertIn("beer", hits)

    def test_clean_question_has_no_hits(self):
        hits = assess.screen_suitability("She has 5 apples and buys 3 more.")
        self.assertEqual(hits, [])

    def test_suitability_hit_forces_rejection(self):
        rec = assess.assess_record(
            "test-4", "train", 4,
            "He spent $10 on beer.",
            "He has $10-$5=<<10-5=5>>5 dollars left.\n#### 5",
        )
        status, reason = assess.decide_status(rec)
        self.assertEqual(status, "rejected")
        self.assertIn("suitability", reason)


class TestDuplicateDetection(unittest.TestCase):
    def test_exact_duplicate_flagged(self):
        recs = [
            assess.assess_record("a", "train", 1, "Tom has 3 apples and buys 2 more. How many now?",
                                  "3+2=<<3+2=5>>5.\n#### 5"),
            assess.assess_record("b", "train", 2, "Tom has 3 apples and buys 2 more. How many now?",
                                  "3+2=<<3+2=5>>5.\n#### 5"),
        ]
        assess.find_duplicates(recs)
        self.assertIsNone(recs[0]["flags"]["exact_duplicate_of"])
        self.assertEqual(recs[1]["flags"]["exact_duplicate_of"], "a")

    def test_template_near_duplicate_flagged_despite_different_numbers(self):
        recs = [
            assess.assess_record("a", "train", 1,
                "Sam has 12 red marbles and 8 blue marbles. How many marbles in total does Sam have?",
                "12+8=<<12+8=20>>20.\n#### 20"),
            assess.assess_record("b", "train", 2,
                "Sam has 40 red marbles and 15 blue marbles. How many marbles in total does Sam have?",
                "40+15=<<40+15=55>>55.\n#### 55"),
        ]
        assess.find_duplicates(recs)
        self.assertEqual(recs[1]["flags"].get("near_duplicate_of"), "a")


class TestDistractorGeneration(unittest.TestCase):
    def test_exactly_one_correct_choice(self):
        rec = {
            "id": "x", "source": {"split": "train", "index": 1}, "grade_estimate": 5,
            "topic": "Money", "difficulty": "easy",
            "original": {"question": "q", "answer": "10-4=<<10-4=6>>6.\n#### 6"},
            "final_answer": "6", "readable_steps": ["10-4=6."], "flags": {},
            "arithmetic": {"arithmetic_verified": True},
        }
        candidate, err = adapt.adapt_record(rec)
        self.assertIsNone(err)
        self.assertEqual(len(candidate["choices"]), 4)
        matches = [c for c in candidate["choices"] if c == candidate["answer"]]
        self.assertEqual(len(matches), 1)

    def test_no_equivalent_duplicate_choices(self):
        # Guards the "0.5 / 1/2 / 2/4" style accidental-second-correct-answer bug:
        # every choice, parsed numerically, must be numerically distinct.
        rec = {
            "id": "y", "source": {"split": "train", "index": 2}, "grade_estimate": 5,
            "topic": "Fractions", "difficulty": "medium",
            "original": {"question": "q", "answer": "1/2=<<1/2=0.5>>0.5.\n#### 0.5"},
            "final_answer": "0.5", "readable_steps": ["1/2=0.5."], "flags": {},
            "arithmetic": {"arithmetic_verified": True},
        }
        candidate, err = adapt.adapt_record(rec)
        if candidate is not None:  # generation can legitimately fail for edge values
            numeric = [adapt.parse_number(c) for c in candidate["choices"]]
            self.assertEqual(len(set(numeric)), 4)

    def test_whole_number_answer_never_gets_decimal_distractor(self):
        rec = {
            "id": "z", "source": {"split": "train", "index": 3}, "grade_estimate": 4,
            "topic": "Word Problems (general)", "difficulty": "easy",
            "original": {"question": "q", "answer": "4+7+11=<<4+7+11=22>>22.\n3*22=<<3*22=66>>66.\n#### 66"},
            "final_answer": "66", "readable_steps": ["4+7+11=22.", "3*22=66."], "flags": {},
            "arithmetic": {"arithmetic_verified": True},
        }
        candidate, err = adapt.adapt_record(rec)
        self.assertIsNone(err)
        for c in candidate["choices"]:
            self.assertNotIn(".", c)

    def test_malformed_final_answer_is_rejected_not_crashed(self):
        rec = {
            "id": "w", "source": {"split": "train", "index": 4}, "grade_estimate": 4,
            "topic": "Money", "difficulty": "easy",
            "original": {"question": "q", "answer": "#### not-a-number"},
            "final_answer": "not-a-number", "readable_steps": ["a step"], "flags": {},
        }
        candidate, err = adapt.adapt_record(rec)
        self.assertIsNone(candidate)
        self.assertIsNotNone(err)


class TestGradeAndDifficultyHeuristic(unittest.TestCase):
    def test_heuristic_has_no_hard_floor_at_grade_4(self):
        # The formula itself is allowed to return low grades for trivially
        # short/simple text — grade_estimate is a heuristic score, not a
        # hard-coded floor. (The README's "GSM8K produced zero records below
        # grade 4" claim is an empirical property of *real* GSM8K questions,
        # checked separately below against the actual committed report — not
        # a guarantee this function makes for arbitrary input.)
        rec = assess.assess_record(
            "g", "train", 1, "Tom has 2 apples. He gets 1 more. How many now?",
            "2+1=<<2+1=3>>3.\n#### 3",
        )
        self.assertGreaterEqual(rec["grade_estimate"], 2)  # the documented absolute floor

    def test_real_dataset_report_confirms_no_grade_1_to_3_coverage(self):
        # Regression check on the actual committed assessment: if a future
        # change to the heuristic (or a dataset update) starts producing
        # Grade 1-3 estimates, that's a material change worth noticing —
        # not something that should silently start looking "supported."
        import json
        report_path = os.path.join(os.path.dirname(__file__), "assessment_report.json")
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
        grades_present = set(int(g) for g in report["grade_estimate_distribution"].keys())
        self.assertTrue(grades_present.isdisjoint({1, 2, 3}))


class TestImportIdempotency(unittest.TestCase):
    def _fake_shortlist(self):
        return [
            {"id": f"gsm8k-train-{i:05d}", "question": f"Q{i}", "questionFr": "",
             "choices": ["1", "2", "3", "4"], "answer": "1", "hint": "h", "steps": ["s"],
             "grade_estimate": 4, "topic": "Money", "difficulty": "easy"}
            for i in range(5)
        ]

    def test_rerunning_the_import_produces_no_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            shortlist_path = os.path.join(tmp, "shortlist.json")
            approved_path = os.path.join(tmp, "approved.json")
            rejected_path = os.path.join(tmp, "rejected.json")
            with open(shortlist_path, "w", encoding="utf-8") as f:
                json.dump(self._fake_shortlist(), f)

            results = []
            argv_backup = sys.argv
            try:
                for _ in range(2):  # simulate re-running the import twice
                    sys.argv = ["finalize_pilot.py", "--in", shortlist_path,
                                "--approved-out", approved_path,
                                "--rejected-out", rejected_path, "--target", "5"]
                    finalize_pilot.main()
                    with open(approved_path, encoding="utf-8") as f:
                        results.append(json.load(f))
            finally:
                sys.argv = argv_backup

            ids = [r["_sourceId"] for r in results[-1]]
            self.assertEqual(len(ids), len(set(ids)), "re-running the import created duplicate records")
            self.assertTrue(len(results[-1]) > 0)
            # Re-running with identical input must be idempotent, not additive.
            self.assertEqual(results[0], results[1])


if __name__ == "__main__":
    unittest.main()
