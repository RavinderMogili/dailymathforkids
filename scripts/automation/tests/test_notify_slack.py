import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notify_slack  # noqa: E402


class TestNotifySlack(unittest.TestCase):
    def test_rejects_unknown_level(self):
        with self.assertRaises(ValueError):
            notify_slack.notify(level="totally_routine_progress_update", title="x")

    @patch.dict(os.environ, {}, clear=False)
    def test_falls_back_to_stderr_when_webhook_missing(self):
        os.environ.pop(notify_slack.WEBHOOK_ENV_VAR, None)
        delivered = notify_slack.notify(level="blocked", title="test blocker", detail="details here")
        self.assertFalse(delivered)

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.test/fake"})
    @patch.object(notify_slack, "_post_to_slack", return_value=True)
    def test_posts_when_webhook_configured(self, mock_post):
        delivered = notify_slack.notify(
            level="ready_for_review", title="done", branch="agent/x", pr_url="https://example.com/pr/1"
        )
        self.assertTrue(delivered)
        mock_post.assert_called_once()
        _, payload = mock_post.call_args[0]
        self.assertIn("READY FOR RAVINDER REVIEW", payload["text"])
        self.assertIn("agent/x", payload["text"])
        self.assertIn("https://example.com/pr/1", payload["text"])

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.test/fake"})
    @patch.object(notify_slack, "_post_to_slack", return_value=True)
    def test_only_four_levels_exist(self, mock_post):
        # Structural guarantee: the set of things that can page Ravinder is
        # fixed and small, not whatever string a call site invents.
        self.assertEqual(
            set(notify_slack.LEVELS.keys()),
            {"blocked", "risky_action", "repeated_failure", "ready_for_review"},
        )


if __name__ == "__main__":
    unittest.main()
