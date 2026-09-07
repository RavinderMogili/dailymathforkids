# Automation V1

A semi-autonomous development pipeline:

```
task -> isolated agent workspace -> implementation -> automatic validation
-> automated tests -> independent AI review -> repair loop
-> Slack notification (blockers only) -> draft PR -> Ravinder approval -> merge
```

Everything up to and including "draft PR" is automatic. Approval and merge
are not — there is no code path anywhere in `scripts/automation/` that
merges a PR, pushes to `main`, force-pushes, or deploys. That boundary is
enforced in three independent places (defense in depth), not just by
convention:

1. `.claude/settings.json` in this worktree denies the risky Bash patterns
   (force-push, `reset --hard`, `merge`, `rebase`, `vercel --prod`,
   `supabase db push/reset`, etc.) at the tool-permission level for any
   Claude Code session running here, interactive or headless.
2. `scripts/automation/config.py`'s `assert_command_is_safe()` re-checks
   every command any automation script shells out, independent of (1).
3. `scripts/automation/config.py`'s `assert_on_agent_branch()` refuses to
   let any script commit, push, or open a PR unless the current branch is
   under the `agent/` namespace — never `main`, never another branch.
   `create_pr.py` additionally contains no function capable of merging.

## Components

| File | Role |
|---|---|
| `config.py` | Shared safety guards: protected-branch check, denied-command check, cross-platform subprocess wrapper. |
| `validation_gate.py` | The "automatic validation + automated tests" step. Fail-closed: real exit codes, nothing swallowed. Runs jest, a Python syntax check, the quiz content validator (conditionally), a secret-shape scan of the diff, and Playwright (opt-in only — see below). |
| `repair_loop.py` | Runs `validation_gate`; on failure, asks the local `claude` CLI (headless `-p` mode) to fix it, up to `MAX_REPAIR_ATTEMPTS` (3) times. Escalates to Slack only once attempts are exhausted. |
| `ai_review.py` | Independent, advisory-only review of the diff via the local `claude` CLI. Never blocks the pipeline. Not a substitute for `/code-review ultra`, which is user-triggered and billed and cannot be launched by automation. |
| `create_pr.py` | Opens a **draft** PR via the GitHub REST API. No merge capability exists in this file. |
| `notify_slack.py` | The only way any script talks to Slack. Exactly four message kinds exist (`blocked`, `risky_action`, `repeated_failure`, `ready_for_review`) — routine progress has no code path to Slack. |
| `orchestrator.py` | Wires the above into one pipeline: `python scripts/automation/orchestrator.py --task "..." [--implement] [--dry-run]`. |

Tests: `scripts/automation/tests/test_*.py`, run with
`python -m unittest discover -s scripts/automation/tests -p "test_*.py"`.
27 tests, all passing as of this writing, covering the safety guards, the
secret scanner (including that it ignores removed/context lines and
catches real additions), the conditional quiz-validator logic, and that
`create_pr.py` structurally contains no merge call.

## Isolation from the other two parallel tasks

Built in a dedicated worktree (`dailymathforkids-main-automation-v1-wt`)
on branch `agent/automation-v1`, branched from `origin/main` — not from
the in-flight `feature/practice-word-problems-pilot` branch, and not
touching the working directories used by the master bug-fix or
content-integration tasks. All new files live under `scripts/automation/`,
`.claude/settings.json`, and `.github/workflows/agent-automation.yml` —
a brand-new workflow file, so it cannot merge-conflict with edits the
other two tasks make to `test.yml` or `daily.yml`.

## Audit: existing CI fails open, not closed

`.github/workflows/daily.yml` wraps its validation and test steps in
`|| true`:

```
python scripts/validate_quiz.py --fix || true
...
python scripts/validate_quiz.py || true      # comment even says "deploy regardless"
...
npx jest scripts/validate_quiz.test.js --verbose || true
```

This means a broken validator or a failing test currently cannot stop
that workflow from committing and publishing a quiz. That's a real
"required checks don't fail closed" problem, exactly the pattern flagged
as a concern.

**This is not fixed here.** `daily.yml` generates and validates the exact
question content the 8,500-question content-integration task is actively
expanding, so rewriting its failure handling right now risks colliding
with in-flight work on the same file and the same validator it calls.
See "Deferred" below.

`test.yml` has no `|| true` — it's a clean two-step jest run and needed no
change.

`agent-automation.yml` (new, this task) is fail-closed throughout: every
step's real exit code gates the job, and the two `|| true`-shaped
exceptions in the design (the AI review step, and the opt-in e2e job) are
each individually justified in the workflow file's own comments — the
review step is advisory by design and its script always exits 0, and the
e2e job is a separate opt-in workflow, not a masked failure in the main
gate.

## Audit: Playwright e2e targets production

`e2e/full-flow.spec.js` and its siblings hit `https://dailymathforkids.com`
and the live API at `https://dailymathforkids-api.vercel.app`;
`e2e/global-teardown.js` uses `SUPABASE_SERVICE_ROLE` against the real
Supabase project. Running that suite is a **production-affecting action**
(it creates and later cleans up real rows), not a read-only check — so it
does not belong in the "safe, always-automatic" bucket the way jest does.

`validation_gate.py` skips it by default and only runs it when
`RUN_E2E_AGAINST_PROD=1` is explicitly set; `agent-automation.yml` mirrors
that as a separate `workflow_dispatch`-only job, never on every push/PR.

## Manual setup required (cannot be done by an agent)

1. **Slack webhook.** Create a Slack Incoming Webhook and set it as the
   `SLACK_WEBHOOK_URL` secret in GitHub (Settings → Secrets and variables →
   Actions) for the automated CI notifications, and export it locally
   (`export SLACK_WEBHOOK_URL=...`) if running `orchestrator.py` by hand.
   Without it, notifications print to stderr with a
   `[SLACK NOT CONFIGURED]` prefix instead of failing silently.
2. **GitHub token for PR creation.** `create_pr.py` needs a `GITHUB_TOKEN`
   in the environment with `Pull requests: write` on this repo (a
   fine-grained PAT is enough) to actually open the draft PR. Without it,
   the script prints what it would have done and exits without creating
   anything — safe, but you'll need to open the PR by hand until the
   token exists.
3. **`gh` CLI** is not installed in this environment; PR creation goes
   through the raw GitHub REST API instead (`create_pr.py`), so `gh` is
   not required, but installing it is fine if preferred later.
4. Decide who reviews the AI-review-step output — it's a first draft, not
   a substitute for `/code-review ultra`, which stays a manual,
   user-triggered, billed step.

## Known risks

- `ai_review.py` and `repair_loop.py` shell out to the local `claude` CLI.
  In CI, that means installing `@anthropic-ai/claude-code` via npm and
  authenticating with `ANTHROPIC_API_KEY` — verify that package name and
  the CLI's non-interactive `-p` behavior against whatever CLI version
  actually ends up pinned in CI before relying on this unattended, since
  CLI flags/auth behavior can change between releases.
- The repair loop's automatic fix attempts are bounded (3) and scoped by
  `.claude/settings.json`'s deny list, but an LLM-driven repair attempt
  editing arbitrary files in the worktree is still less predictable than
  a human diff. Read `scripts/automation/output/review-*.md` before
  trusting a repaired PR.
- The secret scanner is pattern-based (Anthropic/OpenAI-shaped keys, JWT-
  shaped tokens, PEM private key headers) and only scans the diff against
  `origin/main`. It is a safety net, not a guarantee — it will miss novel
  secret formats.
- `agent-automation.yml`'s jobs are gated on `startsWith(..., 'agent/')`;
  if a future agent branch is created outside that naming convention, this
  gate silently won't run for it. Worth a periodic check.

## Deferred due to active parallel work

- **`daily.yml`'s `|| true` failure-masking** (master-bug-fix /
  content-integration overlap): not rewritten here because it's the same
  file and same validator (`scripts/validate_quiz.py`) the
  content-integration task is actively expanding. Recommended fix once
  that work lands: replace each `|| true` around
  `validate_quiz.py`/jest with a real exit-code check, and make the
  final "deploy regardless" step an explicit, logged decision rather than
  an unconditional `|| true` — if quiz generation is broken, failing loud
  (and Slack-notifying) beats silently publishing a bad quiz.
- No changes were made to `test.yml`, `scripts/gen_site.py`, or
  `scripts/validate_quiz.py` themselves, for the same reason.

## Recommended integration order

1. Merge this branch's new files first (`scripts/automation/`,
   `.claude/settings.json`, `.github/workflows/agent-automation.yml`) —
   they're all net-new paths, so this should be a clean, low-risk merge
   regardless of what state the other two tasks are in.
2. Once the content-integration task's changes to `validate_quiz.py` /
   `gen_site.py` land, revisit the deferred `daily.yml` fail-closed fix
   above as its own small PR.
3. Set up the Slack webhook and `GITHUB_TOKEN` secrets (see Manual setup)
   before relying on `orchestrator.py` for a real task end-to-end.
