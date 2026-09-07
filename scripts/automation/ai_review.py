"""
Independent AI review step for Automation V1.

This is deliberately advisory only -- it never blocks the pipeline and its
exit code is always 0. It writes a review to scripts/automation/output/
review-<branch>.md so it can be linked from the PR body.

Note on scope: this project's Claude Code environment has a separate,
user-triggered "ultra" review (/code-review ultra, launches a billed
multi-agent cloud review). That command cannot be launched by an
automation script -- it requires a human to trigger it interactively and
be billed for it -- so it is NOT what this script does. This script instead
does a normal, single-pass review via the local `claude` CLI, useful as a
fast first-pass "does this look right" check before Ravinder's own review
(which can still include running /code-review ultra by hand). Treat this
script's output as a draft reviewer's notes, not a substitute for that.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

REVIEW_PROMPT_TEMPLATE = """\
Review the following diff for correctness bugs, security issues, and
reuse/simplification opportunities. Do not restate what the diff does line
by line. Be specific: cite file paths and reason about concrete failure
scenarios, not style preferences. If nothing is wrong, say so plainly.

Diff (branch {branch} against {base_ref}):
```diff
{diff}
```
"""


def _get_diff(base_ref: str) -> str:
    result = subprocess.run(
        ["git", "diff", f"{base_ref}...HEAD"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return result.stdout


def run(base_ref="origin/main") -> Path:
    branch = config.current_branch()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"review-{branch.replace('/', '_')}.md"

    diff = _get_diff(base_ref)
    if not diff.strip():
        out_path.write_text("No diff against base ref -- nothing to review.\n", encoding="utf-8")
        return out_path

    claude_bin = shutil.which("claude")
    if not claude_bin:
        out_path.write_text(
            "AI review skipped: 'claude' CLI not found on PATH in this environment.\n"
            "Recommend running `/code-review` (or `/code-review ultra` for a deeper "
            "multi-agent pass) by hand before merging.\n",
            encoding="utf-8",
        )
        return out_path

    prompt = REVIEW_PROMPT_TEMPLATE.format(branch=branch, base_ref=base_ref, diff=diff[:60000])
    result = subprocess.run(
        [claude_bin, "-p", prompt, "--permission-mode", "plan"],
        cwd=ROOT, capture_output=True, text=True, timeout=1800,
    )
    review_text = result.stdout.strip() or "(no output from AI review)"
    out_path.write_text(review_text + "\n", encoding="utf-8")
    return out_path


def main():
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    out_path = run(base_ref)
    print(f"AI review written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
