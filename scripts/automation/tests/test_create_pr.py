import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import create_pr  # noqa: E402


class TestParseOwnerRepo(unittest.TestCase):
    def test_https_url(self):
        owner, repo = create_pr._parse_owner_repo("https://github.com/RavinderMogili/dailymathforkids")
        self.assertEqual((owner, repo), ("RavinderMogili", "dailymathforkids"))

    def test_https_url_with_git_suffix(self):
        owner, repo = create_pr._parse_owner_repo("https://github.com/RavinderMogili/dailymathforkids.git\n")
        self.assertEqual((owner, repo), ("RavinderMogili", "dailymathforkids"))

    def test_ssh_url(self):
        owner, repo = create_pr._parse_owner_repo("git@github.com:RavinderMogili/dailymathforkids.git")
        self.assertEqual((owner, repo), ("RavinderMogili", "dailymathforkids"))

    def test_non_github_raises(self):
        with self.assertRaises(ValueError):
            create_pr._parse_owner_repo("https://gitlab.com/foo/bar.git")


class TestBuildPrPayload(unittest.TestCase):
    def test_payload_is_draft_and_targets_base(self):
        payload = create_pr.build_pr_payload(
            "agent/automation-v1", "main", "Build Automation V1", "- [x] jest\n- [x] secret scan",
            "scripts/automation/output/review-agent_automation-v1.md", "None.",
        )
        self.assertTrue(payload["draft"])
        self.assertEqual(payload["head"], "agent/automation-v1")
        self.assertEqual(payload["base"], "main")
        self.assertIn("READY FOR RAVINDER REVIEW", payload["body"])
        self.assertIn("has NOT been merged", payload["body"])

    def test_no_merge_capability_exists_in_module(self):
        # Structural guarantee: nothing in this module can merge a PR.
        module_source = Path(create_pr.__file__).read_text(encoding="utf-8")
        self.assertNotIn("/merge", module_source)
        self.assertNotIn("PUT", module_source)  # GitHub's merge endpoint is a PUT


if __name__ == "__main__":
    unittest.main()
