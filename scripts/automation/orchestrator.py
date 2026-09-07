"""
Automation V1 orchestrator.

Wires the full pipeline described in the automation design:

    task -> isolated agent workspace -> implementation -> automatic
    validation -> automated tests -> independent AI review -> repair loop
    -> Slack notification only for genuine blockers -> final PR/review
    package -> Ravinder approval -> merge

Everything through "final PR/review package" is automatic. "Ravinder
approval" and "merge" are explicitly NOT performed by this script --
there is no code path here that merges a PR, pushes to main, or deploys.

Usage:
  python scripts/automation/orchestrator.py --task "Fix X" [--implement] [--dry-run]

Run this from inside an agent/* worktree (see
scripts/automation/AUTOMATION_V1.md for how to create one). It refuses to
run anywhere else.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import create_pr  # noqa: E402
import notify_slack  # noqa: E402
import repair_loop  # noqa: E402
import ai_review  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _run_implementation(task: str):
    """Ask the local claude CLI to implement `task` in the current worktree.
    Bounded by .claude/settings.json permissions in this worktree (no
    push/merge/deploy tools available to it)."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        raise RuntimeError("'claude' CLI not found on PATH; cannot run --implement.")
    result = subprocess.run(
        [claude_bin, "-p", task, "--permission-mode", "acceptEdits"],
        cwd=ROOT, capture_output=True, text=True, timeout=3600,
    )
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(result.stderr[-2000:], file=sys.stderr)
        raise RuntimeError("Implementation step failed (non-zero exit from claude -p).")


def _commit_if_dirty(message: str):
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True)
    changed = [line[3:] for line in status.stdout.splitlines() if line.strip()]
    if not changed:
        return False
    config.run_safe(["git", "add"] + changed, cwd=ROOT, check=True)
    config.run_safe(["git", "commit", "-m", message], cwd=ROOT, check=True)
    return True


def _push_current_branch(branch: str):
    config.run_safe(["git", "push", "-u", "origin", branch], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description="Automation V1 orchestrator")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--base", default="main")
    parser.add_argument("--implement", action="store_true", help="Actually run the implementation step via claude -p")
    parser.add_argument("--dry-run", action="store_true", help="Skip push/PR creation, print what would happen")
    args = parser.parse_args()

    branch = config.assert_on_agent_branch()
    print(f"[orchestrator] Running on isolated branch: {branch}")

    if args.implement:
        print("[orchestrator] Implementation step...")
        _run_implementation(args.task)
        _commit_if_dirty(f"Automation V1: {args.task}")
    else:
        print("[orchestrator] --implement not passed; assuming implementation already done on this branch.")

    print("[orchestrator] Validation + repair loop...")
    code, steps, attempts = repair_loop.run(base_ref=f"origin/{args.base}", branch_for_report=branch)
    validation_summary = "\n".join(f"- [{'x' if s.passed else ' '}] {s.name}" for s in steps)

    if code != 0:
        print("[orchestrator] BLOCKED. Slack notified. Not creating a PR.")
        return 1

    print("[orchestrator] Independent AI review...")
    review_path = ai_review.run(base_ref=f"origin/{args.base}")

    if args.dry_run:
        print("[orchestrator] --dry-run: skipping push and PR creation.")
        create_pr.create_pr(
            branch, args.base, args.task, validation_summary,
            str(review_path.relative_to(ROOT)), "", dry_run=True,
        )
        return 0

    print("[orchestrator] Pushing branch...")
    _push_current_branch(branch)

    print("[orchestrator] Creating draft PR...")
    pr_url = create_pr.create_pr(
        branch, args.base, args.task, validation_summary,
        str(review_path.relative_to(ROOT)), "",
    )

    notify_slack.notify(
        level="ready_for_review",
        title=f"Automation V1 finished: {args.task}",
        detail=validation_summary,
        branch=branch,
        pr_url=pr_url or "(PR not created -- see logs, likely missing GITHUB_TOKEN)",
    )
    print("[orchestrator] Done. PR is a draft; merge decision is Ravinder's.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
