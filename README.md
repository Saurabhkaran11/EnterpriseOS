# EnterpriseOS

**The AI employee that operates your business.**

A local-first hackathon demo with five connected enterprise tools, realistic seeded data, and resettable SQLite state. No API keys or external accounts are needed.
https://enterprise-os-gamma.vercel.app/


## Start

Requirements: Node.js 22+, npm, and Python 3.11+.

```bash
./scripts/setup.sh
./scripts/preflight.sh
./scripts/start.sh
```

Open [http://localhost:3000](http://localhost:3000). The API runs at [http://localhost:8000](http://localhost:8000), with health at `/health` and interactive docs at `/docs`.

The home page is the **Executive Customer Review** judge dashboard. Select **Start Demo** to watch the deterministic workflow review Inbox, CRM, and Task Tracker records. Execution pauses for approval before any Calendar action; approving completes the meeting preparation and final verified report, while rejecting stops the sensitive action.

Workflow state is stored in local SQLite, so refreshing the dashboard does not lose progress. All H Company, NVIDIA, and AWS badges are explicitly marked **Mock**; no external integration or credential is used.

For the exact two-minute presentation, architecture narrative, backup path, troubleshooting, and judge Q&A, see `DEMO.md`.

For the complete product description, enterprise problem statement, HLD/LLD diagrams, provider data flows, security model, deployment topology, and verified sponsor demo script, see `ENTERPRISEOS_ARCHITECTURE_AND_DEMO.md`.

## H Company computer use

The computer-use layer lives in `backend/computer_use.py` and provides `plan_action`, `execute_browser_goal`, `get_status`, `cancel_execution`, and `health_check` through both real and mock providers. The demo defaults to a deterministic mock harness that navigates only EnterpriseOS routes and stops before meeting confirmation.

The real adapter uses H Company’s official `hai-agents` SDK and Agent Platform session lifecycle with `h/web-surfer-pro`. A small JSON bridge exposes session start, status, changes, and cancellation to FastAPI. Without a key—or if Agent Platform fails—execution falls back visibly to the mock provider.

Hosted computer use cannot open a machine-local `localhost` page. For a real EnterpriseOS browser run, deploy the frontend to a public HTTPS URL and set `ENTERPRISEOS_PUBLIC_URL` to that origin. Local Judge Demo Mode remains fully functional without it.

Optional configuration is documented in `.env.example`. Keep `HCOMPANY_MOCK_MODE=true` for the credential-free hackathon demo.

## NVIDIA reasoning and report artifacts

`backend/reasoning.py` provides one-model NVIDIA reasoning and a deterministic mock. Every risk, action-plan, and verification response is structurally validated. Malformed output receives exactly one repair attempt; timeout or failed repair falls back without interrupting the workflow.

`backend/artifact_storage.py` stores completed reports as both JSON and Markdown. Local storage under `outputs/artifacts` is the default.

Instead of requiring AWS S3 cloud storage, the agent runs securely under **NVIDIA NeMo CLAW / OpenShell** in a policy-governed sandbox, writing reports locally. This satisfies the secure agent execution challenge by isolating the filesystem and restricting network egress via the `openclaw-sandbox.yaml` configuration.

## Manual development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
(cd backend && ../.venv/bin/python -m uvicorn app:app --reload --port 8000)
npm install
npm run dev
```

## Validation

```bash
npm run build
npx tsc --noEmit
(cd backend && ../.venv/bin/python -m unittest -v test_app.py)
(cd backend && ../.venv/bin/python -m unittest -v test_app.py test_computer_use.py test_integrations.py)
```
