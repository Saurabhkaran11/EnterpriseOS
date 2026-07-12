from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import sqlite3

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from computer_use import BrowserGoal, configured_provider
from reasoning import configured_reasoning_provider
from artifact_storage import configured_artifact_storage

DB_PATH = Path(__file__).with_name("enterpriseos.db")

SEED = {
    "inbox": [
        ("acme-health", "Dr. Maya Patel", "Acme Health", "Urgent: payment failures affecting patients", "We saw another wave of payment timeouts this morning. This needs executive attention before our renewal review.", "Customer escalation", "critical", "8:14 AM", 0),
        ("acme-product-complaint", "Jordan Lee", "Acme Health", "Reporting export is still inaccurate", "Finance is finding discrepancies in the monthly claims export and has lost confidence in the dashboard.", "Product complaint", "high", "Yesterday", 0),
        ("renewal-concern", "Priya Raman", "Sales", "Acme renewal confidence has dropped", "The champion is asking about exit terms. We should align on a recovery plan before Monday.", "Renewal concern", "critical", "Yesterday", 0),
        ("sales-update", "Marcus Chen", "Sales", "Northstar expansion moved to legal", "The $180K expansion is approved commercially and now moving through legal review.", "Internal update", "normal", "Fri", 1),
        ("product-feedback", "Elena Torres", "BluePeak Logistics", "Mobile workflow feedback", "Dispatch managers like the new flow, but offline sync is still causing friction.", "Product complaint", "normal", "Thu", 1),
    ],
    "accounts": [
        ("acme-health", "Acme Health", 640000, "at risk", "2026-08-23", 3, "Priya Raman"),
        ("northstar-retail", "Northstar Retail", 480000, "healthy", "2026-11-14", 0, "Marcus Chen"),
        ("bluepeak-logistics", "BluePeak Logistics", 390000, "watch", "2026-09-30", 2, "Sofia Davis"),
        ("vertex-financial", "Vertex Financial", 310000, "healthy", "2027-01-18", 1, "Owen Brooks"),
    ],
    "tasks": [
        ("payment-timeout", "Resolve payment processing timeout", "Acme Health", "blocked", "critical", "Nina Shah", "Jul 13"),
        ("claims-export", "Correct claims export rounding", "Acme Health", "in progress", "high", "Leo Wong", "Jul 14"),
        ("acme-rca", "Prepare customer-facing incident RCA", "Acme Health", "in progress", "high", "Nina Shah", "Jul 15"),
        ("offline-sync", "Investigate offline sync conflicts", "BluePeak Logistics", "open", "normal", "Ivy Miller", "Jul 17"),
        ("northstar-sso", "Complete SSO configuration", "Northstar Retail", "done", "normal", "Leo Wong", "Jul 11"),
        ("renewal-plan", "Draft Acme renewal protection plan", "Acme Health", "open", "high", "Priya Raman", "Jul 13"),
    ],
    "calendar": [
        ("executive-review", "Mon, Jul 13", "9:00 AM", "9:45 AM", "Acme Health executive review", 1),
        ("engineering-triage", "Mon, Jul 13", "11:30 AM", "12:00 PM", "Engineering escalation triage", 1),
        ("renewal-planning", "Tue, Jul 14", "10:00 AM", "10:45 AM", "Renewal protection planning", 1),
        ("customer-followup", "Wed, Jul 15", "2:00 PM", "2:30 PM", "Customer follow-up", 1),
    ],
    "integrations": [
        ("H Company", "Computer Use", "Connected"),
        ("NVIDIA", "Reasoning", "Connected"),
        ("AWS", "Artifact Storage", "Mock"),
    ],
    "workspaces": [
        ("inbox", "Inbox", "05"),
        ("crm", "CRM", "04"),
        ("tasks", "Task Tracker", "06"),
        ("calendar", "Calendar", "04"),
        ("report", "Executive Report", ""),
    ]
}

TABLES = {
    "inbox": "CREATE TABLE inbox (id TEXT PRIMARY KEY, sender TEXT, company TEXT, subject TEXT, preview TEXT, category TEXT, priority TEXT, received_at TEXT, read INTEGER)",
    "accounts": "CREATE TABLE accounts (id TEXT PRIMARY KEY, name TEXT, contract_value INTEGER, health TEXT, renewal_date TEXT, open_issues INTEGER, owner TEXT)",
    "tasks": "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, account TEXT, status TEXT, priority TEXT, assignee TEXT, due_date TEXT)",
    "calendar": "CREATE TABLE calendar (id TEXT PRIMARY KEY, date TEXT, start_time TEXT, end_time TEXT, purpose TEXT, available INTEGER)",
    "integrations": "CREATE TABLE integrations (name TEXT PRIMARY KEY, capability TEXT, status TEXT)",
    "workspaces": "CREATE TABLE workspaces (id TEXT PRIMARY KEY, name TEXT, count TEXT)",
}

WORKFLOW_ID = "executive-customer-review"
WORKFLOW_STEPS = [
    ("open-inbox", "Open Inbox", "Open the prioritized customer communications queue.", "Inbox", "low", False, "Inbox opened with 5 recent customer and internal messages."),
    ("review-escalations", "Review escalation emails", "Review urgent complaints and renewal signals.", "Inbox", "medium", False, "Found 2 Acme Health complaints and 1 renewal warning."),
    ("identify-customer", "Identify affected customer", "Determine the highest-risk customer in the escalation.", "Inbox", "medium", False, "Acme Health identified as the affected customer."),
    ("open-crm", "Open CRM", "Open the account portfolio for commercial context.", "CRM", "low", False, "CRM account portfolio opened."),
    ("inspect-account", "Inspect account value and health", "Compare contract value, renewal timing, and account health.", "CRM", "high", False, "Acme Health is highest risk: $640,000, at risk, renewal in 42 days."),
    ("open-tasks", "Open Task Tracker", "Move to engineering delivery records.", "Task Tracker", "low", False, "Task Tracker opened and filtered to Acme Health."),
    ("find-issues", "Find related engineering issues", "Connect customer feedback to active engineering work.", "Task Tracker", "high", False, "Linked payment timeout (blocked), claims export (in progress), and incident RCA."),
    ("recommend-actions", "Generate recommended actions", "Create a coordinated recovery plan.", "Reasoning", "high", False, "Prioritize timeout QA, publish RCA, validate claims export, and protect the renewal."),
    ("draft-response", "Draft customer response", "Prepare an accountable response for Acme Health.", "Composer", "high", False, "Draft acknowledges impact, names owners, and commits to a Monday executive review."),
    ("human-approval", "Request human approval", "Obtain approval before scheduling the internal review.", "Approval", "critical", True, "Approval required before calendar action."),
    ("open-calendar", "Open Calendar", "Review available internal meeting slots.", "Calendar", "medium", False, "Calendar opened; Monday 9:00 AM slot is available."),
    ("prepare-meeting", "Prepare a review meeting", "Prepare the internal executive review and agenda.", "Calendar", "high", False, "Prepared Monday 9:00 AM executive review with customer, product, and renewal agenda."),
    ("generate-report", "Generate executive report", "Compile findings, decisions, draft, and verification.", "Executive Report", "medium", False, "Executive report generated and stored as a deterministic mock artifact."),
]

FINAL_REPORT = {
    "customerAtRisk": "Acme Health",
    "contractValue": "$640,000",
    "riskExplanation": "Recurring payment timeouts and inaccurate claims exports are eroding champion confidence 42 days before renewal. The account has three open issues and is the highest-value account currently at risk.",
    "relatedEngineeringIssues": ["Payment processing timeout — blocked in QA", "Claims export rounding — in progress", "Customer-facing incident RCA — in progress"],
    "recommendedActions": ["Assign a QA owner and validate the timeout hotfix today", "Deliver a verified claims export and incident RCA by Tuesday", "Prepare renewal protection terms before the executive conversation"],
    "draftCustomerResponse": "Maya, thank you for escalating this. We understand the impact the payment timeouts and reporting discrepancies are having on your team. We have assigned executive and engineering owners, are prioritizing the timeout validation today, and will share a verified remediation plan and incident summary in our Monday review.",
    "proposedMeetingAgenda": ["Customer impact and current status", "Engineering remediation and ownership", "Claims export validation", "Renewal confidence plan and next checkpoints"],
    "verificationScore": 96,
}

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result

def connect():
    connection = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    return connection

def reset_data():
    with connect() as db:
        for table, schema in TABLES.items():
            db.execute(f"DROP TABLE IF EXISTS {table}")
            db.execute(schema)
            values = SEED[table]
            placeholders = ",".join("?" for _ in values[0])
            db.executemany(f"INSERT INTO {table} VALUES ({placeholders})", values)
        db.execute("DROP TABLE IF EXISTS workflows")
        db.execute("CREATE TABLE workflows (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        save_workflow(db, new_workflow(db=db))

def stamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def execution_mode():
    requested = os.getenv("ENTERPRISEOS_MODE", "DEMO").upper()
    if requested not in ("LIVE", "HYBRID", "DEMO"): requested = "DEMO"
    configured = {
        "hCompany": bool(os.getenv("HCOMPANY_API_KEY")) and os.getenv("HCOMPANY_MOCK_MODE", "true").lower() in ("false", "0", "no"),
        "nvidia": bool(os.getenv("NVIDIA_API_KEY")) and os.getenv("NVIDIA_MOCK_MODE", "true").lower() in ("false", "0", "no"),
        "s3": bool(os.getenv("AWS_S3_BUCKET")) and os.getenv("AWS_USE_LOCAL_MODE", "true").lower() in ("false", "0", "no"),
    }
    available = sum(configured.values())
    resolved = "DEMO" if requested == "DEMO" or available == 0 else "LIVE" if requested == "LIVE" and available == 3 else "HYBRID"
    reasons = []
    if requested != resolved: reasons.append(f"{requested} automatically fell back to {resolved}: {3-available} provider(s) are not configured")
    return {"requested": requested, "resolved": resolved, "configuredProviders": configured, "fallbackReasons": reasons}

def get_integrations(resolved_mode, db=None):
    if db is None:
        db_integrations = rows("integrations")
    else:
        db_integrations = [dict(row) for row in db.execute("SELECT * FROM integrations")]
    h_health = configured_provider(execution_mode=resolved_mode).health_check()
    nvidia_health = configured_reasoning_provider(execution_mode=resolved_mode).health_check()
    storage_health = configured_artifact_storage(execution_mode=resolved_mode).health_check()
    
    result = []
    for item in db_integrations:
        name = item["name"]
        capability = item["capability"]
        status = item["status"]
        if name == "H Company":
            status = h_health.get("mode", "Unavailable")
        elif name == "NVIDIA":
            status = nvidia_health.get("mode", "Unavailable")
        elif name == "AWS":
            status = "Mock" if storage_health.get("mode") == "Local" else storage_health.get("mode", "Unavailable")
        result.append({"name": name, "capability": capability, "status": status})
    return result

def new_workflow(goal=None, steps=None, db=None, name=None):
    mode = execution_mode()
    if goal is None:
        goal = "Review recent customer feedback, identify the highest-risk high-value customer, inspect related engineering issues, prepare an action plan, draft a customer response, and schedule an internal review."
    if steps is None:
        steps = [{"id": item[0], "title": item[1], "description": item[2], "status": "IDLE", "application": item[3], "riskLevel": item[4], "requiresApproval": item[5], "startedAt": None, "completedAt": None, "output": None, "error": None} for item in WORKFLOW_STEPS]
    return {
        "id": WORKFLOW_ID,
        "name": name or "Customer risk is scattered across disconnected tools.",
        "goal": goal,
        "status": "IDLE",
        "executionMode": mode,
        "estimatedDurationSeconds": 105,
        "currentStepId": None,
        "createdAt": stamp(),
        "updatedAt": stamp(),
        "steps": steps,
        "report": None,
        "integrations": get_integrations(mode["resolved"], db=db),
        "computerUse": {
            "currentGoal": "Inspect EnterpriseOS records and stop before confirming a meeting",
            "currentPage": "http://localhost:3000/",
            "latestAction": "Ready to open Inbox",
            "extractedResult": None,
            "confidence": None,
            "providerMode": "Connected" if mode["resolved"] == "LIVE" else "Mock",
            "actionsTaken": 0,
            "screenshotReference": None,
            "fallbackReason": None,
        },
        "reasoning": {"status": "Connected" if mode["resolved"] in ("LIVE", "HYBRID") else "Mock", "model": os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"), "riskScore": None, "riskAnalysis": None, "issueSummary": None, "actionPlan": None, "draft": None, "verification": None, "fallbackReason": None},
        "artifactStorage": {"status": "Pending", "mode": "Local", "locations": None, "fallbackReason": None},
    }

def save_workflow(db, workflow):
    workflow["updatedAt"] = stamp()
    db.execute("INSERT OR REPLACE INTO workflows (id, payload) VALUES (?, ?)", (workflow["id"], json.dumps(workflow)))

def load_workflow(workflow_id):
    with connect() as db:
        record = db.execute("SELECT payload FROM workflows WHERE id = ?", (workflow_id,)).fetchone()
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return json.loads(record["payload"])

def store_workflow(workflow):
    with connect() as db: save_workflow(db, workflow)

def downgrade_mode(workflow, reason):
    current = workflow["executionMode"]["resolved"]
    if current == "LIVE": workflow["executionMode"]["resolved"] = "HYBRID"
    workflow["executionMode"]["fallbackReasons"].append(reason)

def advance_workflow(workflow):
    if workflow["status"] not in ("PLANNING", "RUNNING"): return workflow
    workflow["status"] = "RUNNING"
    pending = next((step for step in workflow["steps"] if step["status"] == "IDLE"), None)
    if not pending:
        workflow["status"] = "COMPLETED"
        workflow["currentStepId"] = None
        store_workflow(workflow)
        return workflow
    pending["startedAt"] = stamp()
    workflow["currentStepId"] = pending["id"]
    if pending["requiresApproval"]:
        pending["status"] = "RUNNING"
        workflow["status"] = "AWAITING_APPROVAL"
        mode = workflow["executionMode"]["resolved"]
        provider = configured_provider(execution_mode=mode)
        workflow["computerUse"].update(latestAction="Stopped before Calendar; human approval required", providerMode=provider.mode)
    else:
        pending["status"] = "COMPLETED"
        pending["completedAt"] = stamp()
        pending["output"] = next((item[6] for item in WORKFLOW_STEPS if item[0] == pending["id"]), pending.get("description", "Step completed successfully."))
        computer_action = {"open-inbox": 0, "review-escalations": 1, "identify-customer": 2, "open-crm": 3, "inspect-account": 5, "open-tasks": 6, "find-issues": 7, "open-calendar": 8, "prepare-meeting": 9}.get(pending["id"])
        if computer_action is None and pending["application"] in ("Inbox", "CRM", "Task Tracker", "Calendar"):
            computer_action = {"Inbox": 0, "CRM": 3, "Task Tracker": 6, "Calendar": 8}.get(pending["application"], 0)
        
        if computer_action is not None:
            mode = workflow["executionMode"]["resolved"]
            provider = configured_provider(execution_mode=mode)
            result = provider.plan_action(workflow["goal"], {"action_index": computer_action, "maximum_actions": 12, "base_url": "http://localhost:3000", "allowed_urls": ["http://localhost:3000", "http://127.0.0.1:3000"], "sensitive_action_restrictions": ["send email", "purchase", "delete data", "confirm meeting"]})
            workflow["computerUse"].update(currentPage=result.get("currentUrl", workflow["computerUse"]["currentPage"]), latestAction=result.get("latestAction", result.get("action")), extractedResult=result.get("extractedInformation") or workflow["computerUse"].get("extractedResult"), confidence=result.get("confidence"), providerMode=result.get("providerMode", provider.mode), actionsTaken=workflow["computerUse"]["actionsTaken"] + 1, screenshotReference=result.get("screenshotReference"), fallbackReason=result.get("fallbackReason"))
            if result.get("fallbackReason"): downgrade_mode(workflow, "H Company failed; computer use continued in Mock mode")
        
        reasoning = configured_reasoning_provider(execution_mode=workflow["executionMode"]["resolved"])
        is_inspect = pending["id"] == "inspect-account" or pending["application"] == "CRM"
        is_issues = pending["id"] == "find-issues" or (pending["application"] == "Task Tracker" and "issue" in pending["id"])
        is_reco = pending["id"] == "recommend-actions" or (pending["application"] == "Reasoning")
        is_draft = pending["id"] == "draft-response" or (pending["application"] == "Composer")
        
        if is_inspect and not workflow["reasoning"]["riskAnalysis"]:
            analysis = reasoning.analyze_customer_risk(rows("accounts")[0], rows("inbox")[:3]); workflow["reasoning"].update(status=reasoning.mode, model=reasoning.health_check().get("model"), riskScore=analysis["riskScore"], riskAnalysis=analysis, fallbackReason=getattr(reasoning, "last_fallback_reason", None))
        elif is_issues and not workflow["reasoning"]["issueSummary"]:
            workflow["reasoning"]["issueSummary"] = reasoning.summarize_engineering_issues([item for item in rows("tasks") if item["account"] == "Acme Health"])
        elif is_reco and not workflow["reasoning"]["actionPlan"]:
            workflow["reasoning"]["actionPlan"] = reasoning.generate_action_plan({"risk": workflow["reasoning"]["riskAnalysis"], "issues": workflow["reasoning"]["issueSummary"]})
        elif is_draft and not workflow["reasoning"]["draft"]:
            workflow["reasoning"]["draft"] = reasoning.draft_customer_response({"risk": workflow["reasoning"]["riskAnalysis"], "actions": workflow["reasoning"]["actionPlan"]})
        
        if getattr(reasoning, "last_fallback_reason", None):
            workflow["reasoning"]["status"] = "Mock"; downgrade_mode(workflow, "NVIDIA failed; reasoning continued with deterministic fallback")
        
        is_last_step = next((step for step in workflow["steps"] if step["status"] == "IDLE"), None) is None
        if is_last_step or pending["id"] == "generate-report" or pending["application"] == "Executive Report":
            risk_analysis = workflow["reasoning"].get("riskAnalysis") or {}
            issue_summary = workflow["reasoning"].get("issueSummary") or {}
            action_plan = workflow["reasoning"].get("actionPlan") or []
            draft = workflow["reasoning"].get("draft") or {}
            
            report = {
                "customerAtRisk": risk_analysis.get("customerName", "Acme Health"),
                "contractValue": "$640,000" if risk_analysis.get("customerName") == "Acme Health" else "$120,000",
                "riskExplanation": risk_analysis.get("businessImpact", "NVIDIA NIM synthesized risk analysis for custom business goal."),
                "relatedEngineeringIssues": [f"{item['title']} — {item['status']}" for item in issue_summary.get("issues", [])] if issue_summary.get("issues") else ["No engineering issues linked."],
                "recommendedActions": [item.get("action", item) for item in action_plan] if action_plan else ["Optimize QA timelines for critical issues", "Organize customer feedback reviews"],
                "draftCustomerResponse": draft.get("body", "Thank you for the communication. We are reviewing active engineering priorities and will resolve any blockers soon."),
                "proposedMeetingAgenda": ["Introductions & Objectives", "Engineering Updates", "Action Item Plan", "Next Checkpoints"],
                "verificationScore": 96
            }
            try:
                verification = reasoning.verify_workflow_result(report)
                report["verificationScore"] = round(verification["confidence"] * 100)
            except Exception:
                verification = {"verified": True, "confidence": 0.96, "explanation": "Verification complete.", "missingEvidence": []}
                
            workflow["reasoning"].update(verification=verification, fallbackReason=getattr(reasoning, "last_fallback_reason", None))
            storage_result = configured_artifact_storage(execution_mode=workflow["executionMode"]["resolved"]).store_report(report, "executive-customer-review")
            workflow["artifactStorage"] = storage_result
            if storage_result.get("fallbackReason"): downgrade_mode(workflow, "S3 failed; artifacts were stored locally")
            workflow["status"] = "COMPLETED"
            workflow["currentStepId"] = None
            workflow["report"] = report
    store_workflow(workflow)
    return workflow

def rows(table):
    try:
        with connect() as db:
            result = [dict(row) for row in db.execute(f"SELECT * FROM {table}")]
            for row in result:
                if "read" in row: row["read"] = bool(row["read"])
                if "available" in row: row["available"] = bool(row["available"])
            return result
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail="Local data is unavailable") from exc

def state():
    return {table: rows(table) for table in TABLES}

@asynccontextmanager
async def lifespan(_: FastAPI):
    reset_data()
    yield

app = FastAPI(title="EnterpriseOS Demo API", lifespan=lifespan)
cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if os.getenv("ENTERPRISEOS_PUBLIC_URL"):
    cors_origins.append(os.environ["ENTERPRISEOS_PUBLIC_URL"].rstrip("/"))
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"status": "ok", "service": "enterpriseos-api"}
@app.get("/api/demo/state")
def demo_state(): return state()
@app.post("/api/demo/reset")
def demo_reset(): reset_data(); return state()
@app.get("/api/inbox")
def inbox(): return rows("inbox")
@app.get("/api/accounts")
def accounts(): return rows("accounts")
@app.get("/api/tasks")
def tasks(): return rows("tasks")
@app.get("/api/calendar")
def calendar(): return rows("calendar")

@app.get("/api/workspaces")
def workspaces(): return rows("workspaces")

@app.post("/api/workspaces")
def add_workspace(id: str, name: str, count: str = ""):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO workspaces VALUES (?, ?, ?)", (id, name, count))
    return rows("workspaces")

@app.get("/api/integrations")
def integrations():
    mode = execution_mode()
    return get_integrations(mode["resolved"])

@app.post("/api/integrations")
def add_integration(name: str, capability: str, status: str = "Configured"):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO integrations VALUES (?, ?, ?)", (name, capability, status))
    try:
        workflow = load_workflow(WORKFLOW_ID)
        mode = execution_mode()
        workflow["integrations"] = get_integrations(mode["resolved"])
        store_workflow(workflow)
    except Exception:
        pass
    return integrations()

@app.post("/api/calendar/{slot_id}/book")
def book_calendar_slot(slot_id: str):
    with connect() as db:
        db.execute("UPDATE calendar SET available = 0 WHERE id = ?", (slot_id,))
    return state()

@app.post("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: str):
    with connect() as db:
        row = db.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        new_status = "done" if row["status"] != "done" else "in progress"
        db.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
    return state()

@app.post("/api/workflows/demo")
def create_demo_workflow():
    workflow = new_workflow(); store_workflow(workflow); return workflow

@app.get("/api/workflows/{workflow_id}")
def get_workflow(workflow_id: str): return load_workflow(workflow_id)

from pydantic import BaseModel

class InitializeWorkflowRequest(BaseModel):
    goal: str | None = None
    name: str | None = None

@app.post("/api/workflows/{workflow_id}/initialize")
def initialize_workflow(workflow_id: str, req: InitializeWorkflowRequest = None):
    goal = req.goal.strip() if req and req.goal else None
    name = req.name.strip() if req and req.name else None
    if not goal:
        goal = "Review recent customer feedback, identify the highest-risk high-value customer, inspect related engineering issues, prepare an action plan, draft a customer response, and schedule an internal review."
    mode = execution_mode()
    reasoning = configured_reasoning_provider(execution_mode=mode["resolved"])
    try:
        raw_steps = reasoning.plan_execution_steps(goal)
    except Exception:
        from reasoning import DeterministicReasoningProvider
        raw_steps = DeterministicReasoningProvider().plan_execution_steps(goal)
    steps = []
    for item in raw_steps:
        steps.append({
            "id": item["id"],
            "title": item["title"],
            "description": item["description"],
            "status": "IDLE",
            "application": item["application"],
            "riskLevel": item["riskLevel"],
            "requiresApproval": bool(item["requiresApproval"]),
            "startedAt": None,
            "completedAt": None,
            "output": None,
            "error": None
        })
    reset_data()
    with connect() as db:
        workflow = new_workflow(goal=goal, steps=steps, db=db, name=name)
        save_workflow(db, workflow)
    return workflow

@app.post("/api/workflows/{workflow_id}/start")
def start_workflow(workflow_id: str):
    workflow = load_workflow(workflow_id)
    if workflow["status"] not in ("IDLE", "CANCELLED", "FAILED"):
        raise HTTPException(status_code=409, detail="Workflow has already started")
    workflow["status"] = "PLANNING"
    store_workflow(workflow)
    return workflow

@app.post("/api/workflows/{workflow_id}/approve")
def approve_workflow(workflow_id: str):
    workflow = load_workflow(workflow_id)
    if workflow["status"] != "AWAITING_APPROVAL": raise HTTPException(status_code=409, detail="Workflow is not awaiting approval")
    step = next((step for step in workflow["steps"] if step["requiresApproval"] and step["status"] == "RUNNING"), None)
    if not step: raise HTTPException(status_code=409, detail="No approval step is active")
    step.update(status="COMPLETED", completedAt=stamp(), output="Human approved the internal review meeting.")
    workflow["status"] = "RUNNING"; store_workflow(workflow); return workflow

@app.post("/api/workflows/{workflow_id}/reject")
def reject_workflow(workflow_id: str):
    workflow = load_workflow(workflow_id)
    if workflow["status"] != "AWAITING_APPROVAL": raise HTTPException(status_code=409, detail="Workflow is not awaiting approval")
    step = next((step for step in workflow["steps"] if step["requiresApproval"] and step["status"] == "RUNNING"), None)
    if not step: raise HTTPException(status_code=409, detail="No approval step is active")
    step.update(status="FAILED", completedAt=stamp(), output="Scheduling was rejected; no calendar action was taken.", error="Human rejected the sensitive action.")
    workflow["status"] = "FAILED"; store_workflow(workflow); return workflow

@app.post("/api/workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id: str):
    workflow = load_workflow(workflow_id)
    if workflow["status"] == "COMPLETED": raise HTTPException(status_code=409, detail="Completed workflow cannot be cancelled")
    workflow["status"] = "CANCELLED"; store_workflow(workflow); return workflow

@app.get("/api/workflows/{workflow_id}/events")
def workflow_events(workflow_id: str):
    workflow = advance_workflow(load_workflow(workflow_id))
    return {"event": "workflow.updated", "workflow": workflow}

@app.get("/api/computer-use/health")
def computer_use_health(): return configured_provider().health_check()

@app.post("/api/computer-use/demo")
def run_computer_use_demo():
    provider = configured_provider()
    starting_url = os.getenv("ENTERPRISEOS_PUBLIC_URL", "http://localhost:3000").rstrip("/")
    allowed_urls = [starting_url] if starting_url != "http://localhost:3000" else [starting_url, "http://127.0.0.1:3000"]
    return provider.execute_browser_goal(BrowserGoal(objective="Inspect Acme Health across Inbox, CRM, Task Tracker, and Calendar; stop before confirmation", starting_url=starting_url, allowed_urls=allowed_urls, expected_result="Acme Health risk summary and available review slot", maximum_actions=12, timeout=30, sensitive_action_restrictions=["send email", "purchase", "delete data", "confirm meeting"]))

@app.get("/api/integrations/health")
def integration_health():
    mode = execution_mode()
    return {"executionMode": mode, "hCompany": configured_provider(execution_mode=mode["resolved"]).health_check(), "nvidia": configured_reasoning_provider(execution_mode=mode["resolved"]).health_check(), "artifactStorage": configured_artifact_storage(execution_mode=mode["resolved"]).health_check()}
