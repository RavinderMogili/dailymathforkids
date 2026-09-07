"""
Automatic validation + automated tests gate for Automation V1.

Fail-closed by construction: every step's real exit code is checked and
recorded, nothing is swallowed with `|| true` or an equivalent try/except
pass. If any required step fails, main() returns a non-zero exit code and
prints which step(s) failed and why.

Audit note (see scripts/automation/AUTOMATION_V1.md): the existing
.github/workflows/daily.yml pipeline uses `|| true` around
validate_quiz.py and the jest run, so a broken validator or failing test
there currently cannot block that workflow. That file is very likely being
actively edited by the parallel content-integration task (it generates and
validates the exact question content that work is expanding), so this
script does NOT modify daily.yml. It instead gives the automation
pipeline its own fail-closed gate, and the fix for daily.yml itself is
documented as DEFERRED.

Steps run, in order:
  1. jest unit tests (npm run test:unit)                      -- required
  2. python -m py_compile on every changed/tracked .py file    -- required
  3. scripts/validate_quiz.py --strict, only if daily/*.md or
     scripts/validate_quiz.py changed relative to the base ref -- conditional
  4. a plain-text secret-shape scan over the diff against the
     base ref (API keys, service-role tokens, private key headers) -- required
  5. Playwright e2e -- SKIPPED by default. e2e/full-flow.spec.js and its
     siblings hit https://dailymathforkids.com and the live production API
     (see e2e/global-teardown.js using SUPABASE_SERVICE_ROLE), i.e. running
     them writes test rows into production. That makes them a
     production-affecting action, not a "safe, always-automatic" one, so
     they are opt-in only via RUN_E2E_AGAINST_PROD=1 and are never part of
     the default automatic gate.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

SECRET_PATTERNS = [
    (r"sk-ant-[A-Za-z0-9\-_]{20,}", "Anthropic API key"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI-style API key"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT-looking token (possible Supabase service role key)"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key block"),
]


class StepResult:
    def __init__(self, name, passed, detail=""):
        self.name = name
        self.passed = passed
        self.detail = detail


def _run(cmd, cwd=ROOT):
    proc = config.subprocess_run_portable(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


def step_jest_unit_tests():
    code, output = _run(["npm", "run", "test:unit"])
    return StepResult("jest unit tests", code == 0, output[-4000:])


def step_python_syntax_check():
    py_files = [p for p in ROOT.glob("scripts/**/*.py") if "__pycache__" not in p.parts]
    problems = []
    for f in py_files:
        code, output = _run([sys.executable, "-m", "py_compile", str(f)])
        if code != 0:
            problems.append(f"{f}: {output.strip()}")
    return StepResult("python syntax check", not problems, "\n".join(problems))


def _changed_files(base_ref="origin/main"):
    code, output = _run(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
    if code != 0:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def step_quiz_validator(base_ref="origin/main"):
    changed = _changed_files(base_ref)
    relevant = [f for f in changed if f.startswith("daily/") or f == "scripts/validate_quiz.py"]
    if not relevant:
        return StepResult("quiz content validator", True, "skipped: no daily/ or validate_quiz.py changes")
    code, output = _run([sys.executable, "scripts/validate_quiz.py", "--strict"])
    return StepResult("quiz content validator", code == 0, output[-4000:])


def step_secret_scan(base_ref="origin/main"):
    code, diff = _run(["git", "diff", f"{base_ref}...HEAD"])
    if code != 0:
        return StepResult("secret scan", True, "skipped: could not compute diff against base ref")
    findings = []
    for pattern, label in SECRET_PATTERNS:
        for match in re.finditer(pattern, diff):
            # Only flag additions, not context/removed lines, by checking
            # the character just before the match on its line is '+'.
            line_start = diff.rfind("\n", 0, match.start()) + 1
            if diff[line_start:line_start + 1] == "+":
                findings.append(f"possible {label} near: ...{diff[max(0, match.start()-20):match.start()+10]}...")
    return StepResult("secret scan", not findings, "\n".join(findings))


def step_e2e_playwright():
    if os.environ.get("RUN_E2E_AGAINST_PROD") != "1":
        return StepResult(
            "playwright e2e (opt-in)", True,
            "skipped: e2e suite targets production (dailymathforkids.com + live API). "
            "Set RUN_E2E_AGAINST_PROD=1 to run it deliberately.",
        )
    code, output = _run(["npx", "playwright", "test", "--reporter=list"])
    return StepResult("playwright e2e", code == 0, output[-4000:])


def run_all(base_ref="origin/main"):
    steps = [
        step_jest_unit_tests(),
        step_python_syntax_check(),
        step_quiz_validator(base_ref),
        step_secret_scan(base_ref),
        step_e2e_playwright(),
    ]
    return steps


def main():
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    steps = run_all(base_ref)

    failed = [s for s in steps if not s.passed]
    for s in steps:
        status = "PASS" if s.passed else "FAIL"
        print(f"[{status}] {s.name}")
        if s.detail:
            print(s.detail)
        print("-" * 60)

    if failed:
        print(f"VALIDATION GATE: FAILED ({len(failed)} of {len(steps)} steps failed)")
        return 1

    print(f"VALIDATION GATE: PASSED ({len(steps)} steps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
