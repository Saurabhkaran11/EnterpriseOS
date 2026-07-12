# EnterpriseOS Judge Demo

## Exact startup commands

```bash
./scripts/setup.sh
./scripts/preflight.sh
./scripts/start.sh
```

For a credential-free presentation, leave `ENTERPRISEOS_MODE=DEMO`. The application takes approximately 90–110 seconds of automated execution, plus the time spent explaining and approving.

## Exact URLs

- Judge dashboard: http://localhost:3000
- API health: http://localhost:8000/health
- API documentation: http://localhost:8000/docs
- Supporting workspaces: `/workspace/inbox`, `/workspace/crm`, `/workspace/tasks`, `/workspace/calendar`, `/workspace/report`

## One-minute setup checklist

1. Run `./scripts/preflight.sh` and confirm zero failures.
2. Run `./scripts/reset-demo.sh`.
3. Run `./scripts/start.sh` and open http://localhost:3000.
4. Confirm the persistent mode indicator says **DEMO**.
5. Click **Present ⛶** and verify the report panel says “Report pending.”
6. Keep a terminal ready with `./scripts/run-demo.sh` as the backup.

## Two-minute demo script

**0:00–0:15 — Problem and objective.** “Customer risk is scattered across email, CRM, engineering, and calendars. EnterpriseOS takes one business objective and operates the workflow.” Point to the exact objective and architecture strip.

**0:15–0:25 — Planning.** Click **Start Demo**. Point out `PLANNING`, the execution plan, and the provider badges.

**0:25–1:05 — Computer use and reasoning.** Follow the controlled application preview as H Company opens Inbox, highlights the Acme escalation, moves to CRM, and connects the $640K at-risk account to engineering work. Point to the computer-use activity feed. When NVIDIA reasoning runs, point to the 92/100 risk score.

**1:05–1:20 — Human control.** At `AWAITING APPROVAL`, explain that EnterpriseOS stops before the sensitive calendar action. Click **Approve**.

**1:20–1:50 — Outcome.** Show Calendar preparation, the verified executive report, 96% confidence, and the JSON/Markdown artifact locations. Scroll the completed audit timeline to show every recorded step.

**1:50–2:00 — Close.** “One objective became a verified, auditable operating outcome—with deterministic fallbacks if any sponsor service is unavailable.”

## Architecture explanation

```text
User Goal
  → SQLite-backed Workflow Engine
  → H Company Computer Use provider (controlled EnterpriseOS URLs only)
  → NVIDIA Reasoning provider (validated structured outputs)
  → Human Approval boundary
  → Amazon S3 or Local Artifact storage
```

The Next.js/TypeScript frontend polls the FastAPI backend. Workflow state is stored in SQLite, so refreshes do not lose progress. Provider interfaces isolate external services and fail safely to deterministic implementations.

## Sponsor usage explanation

- **H Company:** Plans computer-use actions and navigates only the controlled EnterpriseOS Inbox, CRM, Task Tracker, and Calendar. It never confirms a meeting without approval. DEMO mode runs the same scripted trajectory.
- **NVIDIA:** Uses one NVIDIA-hosted model for structured risk analysis, issue summaries, action planning, response drafting, and final verification. Invalid output receives one repair attempt before deterministic fallback.
- **Amazon S3:** Stores the final report as JSON and Markdown. If S3 is not configured or fails, both files are written locally and the UI reports `Local` honestly.

## Backup demo instructions

If the browser or network becomes unreliable:

```bash
./scripts/reset-demo.sh
./scripts/run-demo.sh
```

This runs the complete DEMO workflow synchronously, including approval, and prints the final risk score, verification score, and artifact locations. Open `outputs/artifacts/executive-customer-review.md` to present the result.

## Troubleshooting

- **Dashboard says service unavailable:** Confirm `curl http://localhost:8000/health`, then restart `./scripts/start.sh`.
- **Port already in use:** Stop the existing EnterpriseOS process, then start once. Do not run two copies.
- **Workflow appears paused:** `AWAITING APPROVAL` is intentional. Click **Approve** or **Reject**.
- **Wrong or stale state:** Run `./scripts/reset-demo.sh` and refresh.
- **Provider badge is Mock or mode downgraded:** This is expected without credentials or after a provider failure. DEMO remains complete.
- **Artifact missing:** Run `./scripts/run-demo.sh`; verify `outputs/artifacts` is writable.
- **Dependency issue:** Run `./scripts/setup.sh`, followed by `./scripts/preflight.sh`.

## Likely judge questions

### 1. Is this a hard-coded video?

No. It is a live state machine backed by SQLite. Each poll advances one persisted step, updates the controlled application preview, generates outputs, pauses for approval, and writes real JSON and Markdown artifacts. DEMO mode makes provider outputs deterministic for presentation reliability.

### 2. What happens if H Company, NVIDIA, or S3 fails?

LIVE automatically downgrades to HYBRID; if no real providers remain, the safe DEMO path is available. Each fallback is recorded and displayed. The workflow never crashes because a sponsor API is unavailable.

### 3. Where is the human in the loop?

The engine stops at `AWAITING_APPROVAL` before calendar preparation. Rejection marks the sensitive step failed and prevents Calendar access; approval is timestamped in the audit timeline.

### 4. How do you prevent unsafe computer use?

Navigation is restricted to localhost or the configured demo domain, action and timeout limits are enforced, and email, purchases, deletion, and meeting confirmation are blocked.

### 5. What would productionization require?

Managed persistence, authenticated users, secrets management, durable job execution, observability, provider-specific browser infrastructure, and production data connectors. Those are intentionally outside this hackathon demo.
