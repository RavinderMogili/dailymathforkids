"""
Shared configuration and safety guards for the Automation V1 pipeline.

This module is the single place that defines what counts as a "protected"
branch/command. Every script in scripts/automation/ imports its guards from
here instead of re-implementing the checks, so tightening a rule in one
place tightens it everywhere.
"""

import platform
import re
import subprocess

# Branches automation is never allowed to commit to, push to, or open a PR
# targeting as a source of automated changes.
PROTECTED_BRANCHES = {"main", "master"}

# Automated branches must match this prefix. Refusing to operate on branches
# outside this namespace stops the automation from ever touching a branch
# that belongs to a human or to one of the other parallel AI tasks.
AGENT_BRANCH_PREFIX = "agent/"

MAX_REPAIR_ATTEMPTS = 3

# Command substrings that must never be executed by any automation script,
# regardless of what an LLM-generated repair step suggests. This is
# defense-in-depth on top of .claude/settings.json's permission deny list:
# that file governs interactive Claude tool calls, this governs subprocess
# calls made directly by these Python scripts.
DENIED_COMMAND_PATTERNS = [
    r"push\s+.*--force",
    r"push\s+.*-f\b",
    r"push\s+origin\s+(HEAD:)?main\b",
    r"reset\s+--hard",
    r"clean\s+-f",
    r"branch\s+-D",
    r"\bmerge\b",
    r"\brebase\b",
    r"gh\s+pr\s+merge",
    r"vercel\s+.*--prod",
    r"supabase\s+db\s+(push|reset)",
    r"npm\s+publish",
    r"rm\s+-rf\s+/",
]

_DENIED_RE = re.compile("|".join(DENIED_COMMAND_PATTERNS), re.IGNORECASE)


class UnsafeCommandError(RuntimeError):
    pass


class ProtectedBranchError(RuntimeError):
    pass


def assert_command_is_safe(command: str) -> None:
    """Raise UnsafeCommandError if `command` matches a denied pattern."""
    if _DENIED_RE.search(command):
        raise UnsafeCommandError(
            f"Refusing to run command that matches a denied pattern: {command!r}"
        )


def current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def assert_on_agent_branch() -> str:
    """Raise ProtectedBranchError unless HEAD is on an agent/* branch.

    This is the core isolation guarantee: no automation script in this
    package will act (commit, push, open a PR) unless it can prove it is
    running on an isolated automation branch, never on main or a branch
    that doesn't belong to this automation namespace.
    """
    branch = current_branch()
    if branch in PROTECTED_BRANCHES:
        raise ProtectedBranchError(
            f"Refusing to act: current branch '{branch}' is protected."
        )
    if not branch.startswith(AGENT_BRANCH_PREFIX):
        raise ProtectedBranchError(
            f"Refusing to act: current branch '{branch}' is outside the "
            f"'{AGENT_BRANCH_PREFIX}' automation namespace."
        )
    return branch


def run_safe(command_list, **kwargs):
    """subprocess.run wrapper that enforces assert_command_is_safe first."""
    assert_command_is_safe(" ".join(command_list))
    return subprocess_run_portable(command_list, **kwargs)


def subprocess_run_portable(command_list, **kwargs):
    """subprocess.run wrapper that works for npm/npx on Windows.

    On Windows, npm/npx/gh are `.cmd`/`.bat` shims, which the Windows
    CreateProcess API used by subprocess (with shell=False, the default)
    cannot launch directly -- it raises FileNotFoundError even though the
    command is genuinely on PATH. shell=True is needed for exactly those
    shim commands; every other command list stays shell=False (safer:
    the argv list form isn't reinterpreted by a shell). All commands
    passed through this repo's automation scripts are static/hardcoded
    argv lists, never built from untrusted input, so shell=True here does
    not introduce a shell-injection risk.
    """
    needs_shell = platform.system() == "Windows" and command_list and command_list[0] in ("npm", "npx", "gh")
    if needs_shell:
        return subprocess.run(" ".join(command_list), shell=True, **kwargs)
    return subprocess.run(command_list, **kwargs)
