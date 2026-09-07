"""
Bounded repair loop for Automation V1.

Runs the validation gate; if it fails, asks the local `claude` CLI
(headless, non-interactive `-p` mode) to fix the reported failures in
place, then re-runs the gate. Repeats up to MAX_REPAIR_ATTEMPTS times.

This is where "retrying failed tests" and "fixing test failures" (both
listed as things that should run automatically, without Ravinder in the
loop) actually happen. It only ever escalates to Slack -- i.e. only ever
interrupts Ravinder -- once the bounded number of automatic attempts is
exhausted, matching "Slack notification only for genuine blockers".

Guardrails:
  - Refuses to run at all unless config.assert_on_agent_branch() succeeds
    (never repairs code on main or another agent's branch).
  - Never invokes claude with permissions that could push/merge/deploy;
    that boundary is enforced by .claude/settings.json in this worktree,
    which this script does not touch or bypass.
  - If the `claude` CLI isn't on PATH, skips straight to the Slack
    escalation with the raw validation failure instead of silently
    "passing" or hanging.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402
import notify_slack  # noqa: E402
import validation_gate  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _failure_report(steps):
    lines = []
    for s in steps:
        if not s.passed:
            lines.append(f"### {s.name}\n{s.detail}\n")
    return "\n".join(lines)


def _attempt_auto_fix(failure_report: str) -> bool:
    """Ask the local claude CLI to fix the reported failures. Returns True
    if the CLI ran to completion (not whether the fix worked -- that's
    checked by re-running the validation gate)."""
    claude_bin = shutil.which("claude")
    if not claude_bin:
        print("[repair_loop] 'claude' CLI not found on PATH; cannot attempt automatic repair.", file=sys.stderr)
        return False

    prompt = (
        "The Automation V1 validation gate failed on this branch with the "
        "following output. Fix the underlying issue with the smallest "
        "correct change. Do not touch git history, do not force-push, do "
        "not merge, do not modify .github/workflows/daily.yml. Only edit "
        "files needed to make the listed checks pass.\n\n" + failure_report
    )

    result = subprocess.run(
        [claude_bin, "-p", prompt, "--permission-mode", "acceptEdits"],
        cwd=ROOT, capture_output=True, text=True, timeout=1800,
    )
    print(result.stdout[-4000:])
    if result.returncode != 0:
        print(result.stderr[-2000:], file=sys.stderr)
    return result.returncode == 0


def run(base_ref="origin/main", branch_for_report=""):
    branch = branch_for_report or config.current_branch()
    config.assert_on_agent_branch()

    attempt = 0
    steps = validation_gate.run_all(base_ref)
    while any(not s.passed for s in steps) and attempt < config.MAX_REPAIR_ATTEMPTS:
        attempt += 1
        report = _failure_report(steps)
        print(f"[repair_loop] Attempt {attempt}/{config.MAX_REPAIR_ATTEMPTS} to auto-fix:\n{report}")
        ran = _attempt_auto_fix(report)
        if not ran:
            break
        steps = validation_gate.run_all(base_ref)

    still_failing = [s for s in steps if not s.passed]
    if still_failing:
        report = _failure_report(steps)
        notify_slack.notify(
            level="blocked",
            title=f"Validation gate still failing after {attempt} automatic repair attempt(s)",
            detail=report,
            branch=branch,
        )
        return 1, steps, attempt

    return 0, steps, attempt


def main():
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    code, steps, attempts = run(base_ref)
    if code == 0:
        note = "no repair needed" if attempts == 0 else f"fixed after {attempts} automatic attempt(s)"
        print(f"REPAIR LOOP: PASSED ({note})")
    else:
        print(f"REPAIR LOOP: BLOCKED after {attempts} automatic attempt(s); escalated to Slack.")
    return code


if __name__ == "__main__":
    sys.exit(main())
