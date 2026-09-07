"""
Draft PR creation for Automation V1.

By design this module contains no function capable of merging, approving,
or closing a PR -- only opening one, as a draft, targeting `main`. Merging
is a human (Ravinder) action performed in the GitHub UI or CLI, never by
this pipeline. This is a structural guarantee, not just a documented rule:
there is simply no merge call anywhere in this file or anything it imports.

Requires:
  - GITHUB_TOKEN in the environment, with `repo` scope (a fine-grained PAT
    scoped to just this repo is enough: needs "Pull requests: write").
  - `origin` remote pointing at a github.com repo.

Without GITHUB_TOKEN set, run with --dry-run to print the request that
would be made instead of making it (useful for local testing without
credentials, which is what this script's own tests do).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

PR_BODY_TEMPLATE = """\
## Automation V1 -- {branch}

**This PR was prepared by the Automation V1 pipeline. It is a draft and \
has NOT been merged. Merging requires Ravinder's explicit approval.**

### Task
{task_description}

### Validation gate
{validation_summary}

### Independent AI review
See `{review_path}` in this branch for a first-pass automated review. \
This is a draft-reviewer's notes, not a substitute for human review \
(consider `/code-review ultra` before merging anything non-trivial).

### Deferred items (parallel-work overlap)
{deferred_summary}

---
Status: **READY FOR RAVINDER REVIEW**
"""


def _parse_owner_repo(remote_url: str):
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?$", remote_url.strip())
    if not match:
        raise ValueError(f"Could not parse owner/repo from remote URL: {remote_url!r}")
    return match.group(1), match.group(2)


def _origin_owner_repo():
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    )
    return _parse_owner_repo(result.stdout)


def build_pr_payload(branch, base, task_description, validation_summary, review_path, deferred_summary):
    body = PR_BODY_TEMPLATE.format(
        branch=branch,
        task_description=task_description or "(not specified)",
        validation_summary=validation_summary or "(no summary provided)",
        review_path=review_path or "scripts/automation/output/",
        deferred_summary=deferred_summary or "None.",
    )
    return {
        "title": f"[Automation V1] {task_description or branch}"[:250],
        "head": branch,
        "base": base,
        "body": body,
        "draft": True,
    }


def create_pr(branch, base, task_description, validation_summary, review_path, deferred_summary, dry_run=False):
    config.assert_on_agent_branch()
    payload = build_pr_payload(branch, base, task_description, validation_summary, review_path, deferred_summary)

    if dry_run:
        print("[create_pr] --dry-run: would POST this payload:")
        print(json.dumps(payload, indent=2))
        return None

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("[create_pr] GITHUB_TOKEN not set; cannot create PR. Run with --dry-run to preview instead.", file=sys.stderr)
        return None

    owner, repo = _origin_owner_repo()
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[create_pr] Draft PR created: {data.get('html_url')}")
            return data.get("html_url")
    except urllib.error.HTTPError as exc:
        print(f"[create_pr] GitHub API error {exc.code}: {exc.read().decode('utf-8', 'replace')}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Open a draft PR for the current agent branch. Never merges.")
    parser.add_argument("--base", default="main")
    parser.add_argument("--task-description", default="")
    parser.add_argument("--validation-summary", default="")
    parser.add_argument("--review-path", default="")
    parser.add_argument("--deferred-summary", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    branch = config.current_branch()
    url = create_pr(
        branch, args.base, args.task_description, args.validation_summary,
        args.review_path, args.deferred_summary, dry_run=args.dry_run,
    )
    return 0 if (url or args.dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
