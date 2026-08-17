import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import gen_site
import validate_quiz
from validate_quiz import Issue


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "spec" / "conformance-fixtures.json"
INVALID_FIXTURES = ROOT / "scripts" / "fixtures" / "invalid-daily"


class Phase0Tests(unittest.TestCase):
    def test_python_conformance_runner_default_output(self):
        output = ROOT / "data" / "conformance" / "python.json"
        output.unlink(missing_ok=True)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_conformance.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("Python conformance passed:", completed.stdout)
        self.assertTrue(output.exists())

    def test_forbidden_fixes_are_errors_without_mutation(self):
        fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
        from question_quality import conformance_result

        result = conformance_result(fixtures)
        for fixture, actual in zip(fixtures["forbidden_fixes"], result["forbidden_fixes"]):
            with self.subTest(file=fixture["file"]):
                with tempfile.NamedTemporaryFile("w+", encoding="utf-8", delete=False) as handle:
                    path = pathlib.Path(handle.name)
                    handle.write(fixture["stored"])
                before = path.read_bytes()
                self.assertEqual(actual["verdict"], "ERROR")
                self.assertEqual(actual["code"], fixture["code"])
                self.assertEqual(path.read_bytes(), before)
                path.unlink()

    def test_invalid_daily_fixtures_block_publication(self):
        expected_codes = {
            "no-correct-option": "NO_CORRECT_OPTION",
            "two-correct-options": "MULTIPLE_CORRECT_OPTIONS",
            "duplicate-choices": "DUPLICATE_CHOICES",
            "equal-comparison": "EQUAL_OPERANDS_COMPARISON",
            "denominator-one": "FRACTION_DENOMINATOR_ONE",
            "sale-greater-than-original": "SALE_PRICE_GE_ORIGINAL",
            "missing-french": "MISSING_FRENCH",
            "placeholder": "PLACEHOLDER_TEXT",
        }
        for path in sorted(INVALID_FIXTURES.glob("*.md")):
            with self.subTest(fixture=path.name):
                before = path.read_bytes()
                result = validate_quiz.validate_run(path, "2026-01-01")
                self.assertFalse(result["publication_allowed"])
                self.assertTrue(result["blocking_errors"])
                self.assertIn(expected_codes[path.stem], {issue["code"] for issue in result["issues"]})
                self.assertEqual(path.read_bytes(), before)

    def test_allow_nonvalid_allows_warnings_but_not_errors(self):
        question = {"grade": "G3", "num": 1, "question": "unsupported", "en": "unsupported"}
        with patch.object(validate_quiz, "validate_file", return_value=([question], [
            Issue("warning", "G3", 1, "unsupported", "UNVERIFIED")
        ])), patch.object(validate_quiz, "_structural_issues", return_value=[]), \
                patch.object(validate_quiz, "_duplicate_recent_questions", return_value=[]), \
                patch.object(validate_quiz, "_manifest_entries", return_value=[]):
            blocked = validate_quiz.validate_run(pathlib.Path("quiz.md"), "2026-01-01")
            allowed = validate_quiz.validate_run(pathlib.Path("quiz.md"), "2026-01-01", allow_nonvalid=1)
        self.assertFalse(blocked["publication_allowed"])
        self.assertTrue(allowed["publication_allowed"])

        with patch.object(validate_quiz, "validate_file", return_value=([question], [
            Issue("error", "G3", 1, "bad", "NO_CORRECT_OPTION")
        ])), patch.object(validate_quiz, "_structural_issues", return_value=[]), \
                patch.object(validate_quiz, "_duplicate_recent_questions", return_value=[]), \
                patch.object(validate_quiz, "_manifest_entries", return_value=[]):
            result = validate_quiz.validate_run(pathlib.Path("quiz.md"), "2026-01-01", allow_nonvalid=99)
        self.assertFalse(result["publication_allowed"])
        self.assertTrue(result["blocking_errors"])

    def test_manifest_requires_explicit_issue_and_question_identity(self):
        question = {"grade": "G3", "num": 2}
        complete = {
            "reviewer": "R",
            "reviewer_date": "2026-01-02",
            "quiz_date": "2026-01-01",
            "grade": "G3",
            "question_index": 2,
            "code": "UNVERIFIED",
            "worked_verification": "checked",
            "reason": "reviewed",
        }
        self.assertTrue(validate_quiz._manifest_allows(complete, "2026-01-01", question, "UNVERIFIED"))
        for missing in ("reviewer_date", "quiz_date", "grade", "question_index", "code"):
            entry = dict(complete)
            entry.pop(missing)
            self.assertFalse(validate_quiz._manifest_allows(entry, "2026-01-01", question, "UNVERIFIED"))
        self.assertFalse(validate_quiz._manifest_allows(complete, "2026-01-01", question, "NO_CORRECT_OPTION"))
        wrong_question = dict(complete, question_index=1)
        self.assertFalse(validate_quiz._manifest_allows(wrong_question, "2026-01-01", question, "UNVERIFIED"))

    def test_position_bias_is_report_only(self):
        question = {
            "grade": "G3", "num": 1, "question": "2 + 2 = ?", "en": "2 + 2 = ?",
            "fr": "Combien font 2 + 2?", "choices": ["4", "3", "5", "6"],
            "choices_raw": "A) 4 B) 3 C) 5 D) 6", "answer": "4",
        }
        report = {"counts": {"A": 10, "B": 0, "C": 0, "D": 0}, "total": 10,
                  "proportions": {"A": 1.0, "B": 0, "C": 0, "D": 0}, "biased_positions": ["A"]}
        with patch.object(validate_quiz, "validate_file", return_value=([question], [])), \
                patch.object(validate_quiz, "_structural_issues", return_value=[]), \
                patch.object(validate_quiz, "_duplicate_recent_questions", return_value=[]), \
                patch.object(validate_quiz, "_position_report", return_value=report), \
                patch.object(validate_quiz, "_manifest_entries", return_value=[]):
            result = validate_quiz.validate_run(pathlib.Path("quiz.md"), "2026-01-01")
        self.assertTrue(result["publication_allowed"])
        self.assertEqual(result["position_balance"]["biased_positions"], ["A"])
        self.assertNotIn("POSITION_BIAS", [issue["code"] for issue in result["issues"]])

    def test_generation_failure_restores_known_good_files_and_skips_upsert(self):
        with tempfile.TemporaryDirectory() as directory:
            daily = pathlib.Path(directory)
            md_path = daily / "2026-01-01.md"
            html_path = daily / "2026-01-01.html"
            old_md, old_html = b"old markdown\n", b"old html\n"
            md_path.write_bytes(old_md)
            html_path.write_bytes(old_html)
            upserts = []
            with patch.object(gen_site, "DAILY_DIR", daily), \
                    patch.object(gen_site, "LATEST_MARKER", daily / "latest.json"), \
                    patch.object(gen_site, "quiz_date_today", return_value="2026-01-01"), \
                    patch.object(gen_site, "anthropic", object()), \
                    patch.object(gen_site, "OpenAI", None), \
                    patch.object(gen_site, "call_llm", return_value="# invalid"), \
                    patch.object(gen_site, "generate_html_from_text", return_value="<new>"), \
                    patch.object(gen_site, "validate_run", return_value={"publication_allowed": False}), \
                    patch.object(gen_site, "upsert_quiz_to_supabase", side_effect=lambda *args: upserts.append(args)):
                with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}, clear=False):
                    with self.assertRaises(SystemExit):
                        gen_site.safe_generate_today()
            self.assertEqual(md_path.read_bytes(), old_md)
            self.assertEqual(html_path.read_bytes(), old_html)
            self.assertEqual(upserts, [])

    def test_missing_grade_prompt_targets_only_missing_grades(self):
        prompt = "You MUST generate ALL 12 grades (G1 through G12) — do NOT stop early."
        retry = gen_site.build_missing_grade_prompt(prompt, ["G4", "G9"])
        self.assertIn("ONLY these grades: G4, G9", retry)
        self.assertNotIn("generate ALL 12 grades", retry)

    def test_stale_index_uses_served_date_not_today(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            daily = root / "daily"
            daily.mkdir()
            (daily / "2026-08-16.html").write_text("<html>old</html>", encoding="utf-8")
            marker = root / "latest.json"
            marker.write_text(json.dumps({"date": "2026-08-16"}), encoding="utf-8")
            with patch.object(gen_site, "ROOT", root), \
                    patch.object(gen_site, "DAILY_DIR", daily), \
                    patch.object(gen_site, "LATEST_MARKER", marker), \
                    patch.object(gen_site, "quiz_date_today", return_value="2026-08-17"):
                gen_site.rebuild_index_and_sitemap()
            index = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("Latest: 2026-08-16", index)
            self.assertIn("Open quiz for 2026-08-16", index)
            self.assertNotIn("Open today&#39;s problems", index)

    def test_legacy_rewriters_are_absent(self):
        source = (ROOT / "scripts" / "gen_site.py").read_text(encoding="utf-8")
        self.assertNotIn("_deprecated_noop", source)
        self.assertNotIn("review_and_fix_quiz", source)
        self.assertNotIn("auto_fix_answers", source)


if __name__ == "__main__":
    unittest.main()
