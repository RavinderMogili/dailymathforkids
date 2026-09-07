"""
Slack escalation for the Automation V1 pipeline.

Design intent (per the automation spec): Slack should interrupt Ravinder
ONLY for genuine blockers, production/security-sensitive actions, repeated
failures the agent could not resolve on its own, and the final
"ready for review" handoff. Routine progress (tests started, a file was
edited, a repair attempt succeeded) must never page this channel.

This module intentionally only knows four message kinds (see `Level`) to
keep that policy structural rather than a matter of call-site discipline.

Setup required from Ravinder (cannot be done by an agent):
  1. Create a Slack Incoming Webhook (Slack App -> Incoming Webhooks) for
     the channel that should receive escalations.
  2. Set it as the SLACK_WEBHOOK_URL secret in the GitHub repo
     (Settings -> Secrets and variables -> Actions) AND/OR export it as an
     environment variable for local orchestrator runs.

If SLACK_WEBHOOK_URL is not set, notifications are printed to stderr with a
"[SLACK NOT CONFIGURED]" prefix instead of failing silently or crashing the
pipeline -- the underlying validation/test gate still fails closed on its
own exit code regardless of whether Slack delivery succeeds.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

WEBHOOK_ENV_VAR = "SLACK_WEBHOOK_URL"

LEVELS = {
    "blocked": {"emoji": ":no_entry:", "label": "BLOCKED"},
    "risky_action": {"emoji": ":warning:", "label": "RISKY ACTION NEEDS APPROVAL"},
    "repeated_failure": {"emoji": ":repeat:", "label": "REPEATED FAILURE"},
    "ready_for_review": {"emoji": ":white_check_mark:", "label": "READY FOR RAVINDER REVIEW"},
}


def _post_to_slack(webhook_url: str, payload: dict) -> bool:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except urllib.error.URLError as exc:
        print(f"[SLACK] Failed to deliver notification: {exc}", file=sys.stderr)
        return False


def notify(level: str, title: str, detail: str = "", branch: str = "", pr_url: str = "") -> bool:
    if level not in LEVELS:
        raise ValueError(f"Unknown Slack notification level: {level!r}. Must be one of {list(LEVELS)}")

    meta = LEVELS[level]
    lines = [f"{meta['emoji']} *{meta['label']}* — {title}"]
    if branch:
        lines.append(f"Branch: `{branch}`")
    if pr_url:
        lines.append(f"PR: {pr_url}")
    if detail:
        lines.append(f"```{detail[:2500]}```")
    text = "\n".join(lines)

    webhook_url = os.environ.get(WEBHOOK_ENV_VAR, "").strip()
    if not webhook_url:
        print(f"[SLACK NOT CONFIGURED] Would have sent:\n{text}", file=sys.stderr)
        return False

    return _post_to_slack(webhook_url, {"text": text})


def main() -> int:
    parser = argparse.ArgumentParser(description="Send an Automation V1 Slack escalation.")
    parser.add_argument("--level", required=True, choices=list(LEVELS))
    parser.add_argument("--title", required=True)
    parser.add_argument("--detail", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--pr-url", default="")
    args = parser.parse_args()

    delivered = notify(args.level, args.title, args.detail, args.branch, args.pr_url)
    # Always exit 0: failure to deliver a Slack message must never be the
    # reason a CI job goes red, or a real blocker could get masked by a
    # webhook outage. The pipeline's own exit codes are the real gate.
    if not delivered:
        print("[SLACK] Notification not delivered (see above). Pipeline result is unaffected.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
