import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402


class TestAssertCommandIsSafe(unittest.TestCase):
    def test_allows_ordinary_git_commands(self):
        for cmd in ["git status", "git diff origin/main...HEAD", "git add -A", "git commit -m x"]:
            config.assert_command_is_safe(cmd)  # should not raise

    def test_blocks_force_push(self):
        for cmd in ["git push --force", "git push -f origin agent/x", "git push --force-with-lease"]:
            with self.assertRaises(config.UnsafeCommandError):
                config.assert_command_is_safe(cmd)

    def test_blocks_push_to_main(self):
        with self.assertRaises(config.UnsafeCommandError):
            config.assert_command_is_safe("git push origin main")

    def test_blocks_reset_hard(self):
        with self.assertRaises(config.UnsafeCommandError):
            config.assert_command_is_safe("git reset --hard HEAD~1")

    def test_blocks_merge_and_rebase(self):
        with self.assertRaises(config.UnsafeCommandError):
            config.assert_command_is_safe("git merge main")
        with self.assertRaises(config.UnsafeCommandError):
            config.assert_command_is_safe("git rebase main")

    def test_blocks_prod_deploy(self):
        with self.assertRaises(config.UnsafeCommandError):
            config.assert_command_is_safe("vercel deploy --prod")


class TestAssertOnAgentBranch(unittest.TestCase):
    def _mock_branch(self, name):
        return patch.object(config, "current_branch", return_value=name)

    def test_raises_on_main(self):
        with self._mock_branch("main"):
            with self.assertRaises(config.ProtectedBranchError):
                config.assert_on_agent_branch()

    def test_raises_on_non_agent_branch(self):
        with self._mock_branch("feature/something-else"):
            with self.assertRaises(config.ProtectedBranchError):
                config.assert_on_agent_branch()

    def test_allows_agent_branch(self):
        with self._mock_branch("agent/automation-v1"):
            self.assertEqual(config.assert_on_agent_branch(), "agent/automation-v1")


class TestRunSafe(unittest.TestCase):
    def test_raises_before_subprocess_runs(self):
        with self.assertRaises(config.UnsafeCommandError):
            config.run_safe(["git", "push", "--force"])

    def test_runs_safe_command(self):
        result = config.run_safe(
            [sys.executable, "-c", "print('ok')"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
