import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validation_gate  # noqa: E402


class TestSecretScan(unittest.TestCase):
    def _diff_with(self, added_line):
        return (
            "diff --git a/foo.py b/foo.py\n"
            "index 0000000..1111111 100644\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,1 +1,2 @@\n"
            " existing_line = 1\n"
            f"{added_line}\n"
        )

    @patch.object(validation_gate, "_run")
    def test_flags_added_anthropic_style_key(self, mock_run):
        mock_run.return_value = (0, self._diff_with("+api_key = 'sk-ant-abcdefghijklmnopqrstuvwx'"))
        result = validation_gate.step_secret_scan()
        self.assertFalse(result.passed)
        self.assertIn("Anthropic", result.detail)

    @patch.object(validation_gate, "_run")
    def test_ignores_removed_lines(self, mock_run):
        mock_run.return_value = (0, self._diff_with("-api_key = 'sk-ant-abcdefghijklmnopqrstuvwx'"))
        result = validation_gate.step_secret_scan()
        self.assertTrue(result.passed)

    @patch.object(validation_gate, "_run")
    def test_clean_diff_passes(self, mock_run):
        mock_run.return_value = (0, self._diff_with("+print('hello world')"))
        result = validation_gate.step_secret_scan()
        self.assertTrue(result.passed)


class TestQuizValidatorConditional(unittest.TestCase):
    @patch.object(validation_gate, "_changed_files", return_value=["index.html", "styles.css"])
    def test_skips_when_no_daily_content_changed(self, mock_changed):
        result = validation_gate.step_quiz_validator()
        self.assertTrue(result.passed)
        self.assertIn("skipped", result.detail)

    @patch.object(validation_gate, "_run", return_value=(0, "all good"))
    @patch.object(validation_gate, "_changed_files", return_value=["daily/2026-09-07.md"])
    def test_runs_when_daily_content_changed(self, mock_changed, mock_run):
        result = validation_gate.step_quiz_validator()
        self.assertTrue(result.passed)
        mock_run.assert_called_once()


class TestE2ESkippedByDefault(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=False)
    def test_skipped_without_env_flag(self):
        os.environ.pop("RUN_E2E_AGAINST_PROD", None)
        result = validation_gate.step_e2e_playwright()
        self.assertTrue(result.passed)
        self.assertIn("skipped", result.detail)
        self.assertIn("production", result.detail)


if __name__ == "__main__":
    unittest.main()
