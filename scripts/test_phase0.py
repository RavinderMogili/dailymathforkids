import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import gen_site
import quarantine_historical
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
        question = {"grade": "G3", "question_index": 2, "authored_number": 10}
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

    def test_answer_extraction_uses_item_field_indent(self):
        source = """# Daily Math - fixture

## G3
1. **[Easy] First**
   - EN: 2 + 2 = ?
   - FR: 2 + 2 = ?
   - Choices: A) 4  B) 3  C) 5  D) 6
   - Answer: 4
10. **[Hard] Tenth**
    - EN: 3 + 4 = ?
    - FR: 3 + 4 = ?
    - Choices: A) 7  B) 6  C) 8  D) 9
    - Steps:
      - Answer: 99
    - Answer: 7
"""
        questions = validate_quiz.parse_questions_from_md(source)
        self.assertEqual([question["answer"] for question in questions], ["4", "7"])
        self.assertEqual([question["question_index"] for question in questions], [1, 2])
        self.assertEqual([question["authored_number"] for question in questions], [1, 10])

    def test_duplicate_authored_numbers_are_blocking_but_identity_is_ordinal(self):
        source = """# Daily Math - fixture

## G3
1. **[Easy] First**
   - EN: 2 + 2 = ?
   - FR: 2 + 2 = ?
   - Choices: A) 4  B) 3  C) 5  D) 6
   - Answer: 4
10. **[Medium] Tenth**
    - EN: 3 + 4 = ?
    - FR: 3 + 4 = ?
    - Choices: A) 7  B) 6  C) 8  D) 9
    - Answer: 7
10. **[Hard] Also Tenth**
    - EN: 5 + 2 = ?
    - FR: 5 + 2 = ?
    - Choices: A) 7  B) 6  C) 8  D) 9
    - Answer: 7
"""
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "quiz.md"
            path.write_text(source, encoding="utf-8")
            result = validate_quiz.validate_run(path, "2026-01-01")
        self.assertIn("DUPLICATE_QUESTION_NUMBER", {issue["code"] for issue in result["issues"]})

    def test_quarantine_manifest_is_deterministic_and_uses_explicit_keys(self):
        source = """# Daily Math - fixture

## G3
1. **[Easy] First**
   - EN: 2 + 2 = ?
   - FR: 2 + 2 = ?
   - Choices: A) 4  B) 3  C) 5  D) 6
   - Answer: 5
"""
        with tempfile.TemporaryDirectory() as directory:
            daily_dir = pathlib.Path(directory)
            (daily_dir / "2026-01-01.md").write_text(source, encoding="utf-8")
            first = quarantine_historical.build_manifest(daily_dir)
            second = quarantine_historical.build_manifest(daily_dir)
            self.assertEqual(first, second)
            output = daily_dir / "manifest.json"
            quarantine_historical.write_manifest(output, daily_dir)
            first_bytes = output.read_bytes()
            quarantine_historical.write_manifest(output, daily_dir)
            self.assertEqual(first_bytes, output.read_bytes())
            self.assertEqual(first["items"][0]["date"], "2026-01-01")
            self.assertEqual(first["items"][0]["grade"], "G3")
            self.assertEqual(first["items"][0]["question_index"], 1)
            self.assertEqual(first["items"][0]["disposition"], "hidden")
            self.assertEqual(first["items"][0]["restoration_status"], "quarantined")

    def test_quarantine_hiding_requires_exactly_named_item(self):
        manifest = {
            "items": [{
                "date": "2026-01-01",
                "grade": "G3",
                "question_index": 2,
                "disposition": "hidden",
                "restoration_status": "quarantined",
            }]
        }
        self.assertTrue(quarantine_historical.is_quarantined("2026-01-01", "G3", 2, manifest))
        self.assertFalse(quarantine_historical.is_quarantined("2026-01-01", "G3", 1, manifest))
        self.assertFalse(quarantine_historical.is_quarantined("2026-01-01", "G4", 2, manifest))
        self.assertEqual(
            quarantine_historical.filter_archive_dates(
                ["2026-01-02", "2026-01-01"],
                manifest,
            ),
            ["2026-01-02", "2026-01-01"],
        )

    def test_restoration_requires_independent_verification(self):
        manifest = {
            "version": 1,
            "items": [{
                "date": "2026-01-01",
                "grade": "G3",
                "question_index": 1,
                "codes": ["NO_CORRECT_OPTION"],
                "reason": "bad",
                "verification_result": "ERROR",
                "disposition": "hidden",
                "restoration_status": "restored",
                "restoration_verification": "",
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                quarantine_historical.load_manifest(path)

    def test_archive_index_keeps_dates_when_items_are_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            daily = root / "daily"
            quarantine = root / "data" / "quarantine"
            daily.mkdir(parents=True)
            quarantine.mkdir(parents=True)
            (daily / "2026-01-01.html").write_text("<html>bad</html>", encoding="utf-8")
            (daily / "2026-01-02.html").write_text("<html>good</html>", encoding="utf-8")
            (quarantine / "historical.json").write_text(json.dumps({
                "version": 1,
                "items": [{
                    "date": "2026-01-01",
                    "grade": "G3",
                    "question_index": 2,
                    "codes": ["NO_CORRECT_OPTION"],
                    "reason": "bad",
                    "verification_result": "ERROR",
                    "disposition": "hidden",
                    "restoration_status": "quarantined",
                    "restoration_verification": None,
                }],
            }), encoding="utf-8")
            with patch.object(gen_site, "ROOT", root), \
                    patch.object(gen_site, "DAILY_DIR", daily), \
                    patch.object(gen_site, "LATEST_MARKER", root / "latest.json"), \
                    patch.object(gen_site, "quiz_date_today", return_value="2026-01-03"):
                gen_site.rebuild_index_and_sitemap()
            index = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("2026-01-01", index)
            self.assertIn("2026-01-02", index)

    def test_unit_workflows_are_offline_and_content_gates_are_blocking(self):
        workflows = list((ROOT / ".github" / "workflows").glob("*"))
        self.assertTrue(workflows)
        for workflow in workflows:
            text = workflow.read_text(encoding="utf-8")
            self.assertNotIn("|| true", text)
            self.assertNotIn("continue-on-error", text)
            self.assertNotIn("--fix", text)
        unit_workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        self.assertIn("npm run test:unit", unit_workflow)
        self.assertIn("JEST_OFFLINE", unit_workflow)
        self.assertNotIn("SUPABASE_SERVICE_ROLE: ${{ secrets.", unit_workflow)
        self.assertNotIn("upsert-quiz", unit_workflow)

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
