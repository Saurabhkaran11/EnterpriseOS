import os
os.environ["ENTERPRISEOS_MODE"] = "DEMO"
os.environ["HCOMPANY_MOCK_MODE"] = "true"
os.environ["NVIDIA_MOCK_MODE"] = "true"
os.environ["AWS_USE_LOCAL_MODE"] = "true"

import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import app as api

class EnterpriseOSTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        api.DB_PATH = api.Path(self.temp.name) / "test.db"
        api.reset_data()
        self.client = TestClient(api.app)

    def tearDown(self): self.temp.cleanup()

    def test_health(self): self.assertEqual(self.client.get("/health").json()["status"], "ok")
    def test_seed_and_reset(self):
        state = self.client.get("/api/demo/state").json()
        self.assertEqual(state["accounts"][0]["id"], "acme-health")
        self.assertEqual(len(self.client.post("/api/demo/reset").json()["tasks"]), 6)
    def test_collection_endpoints(self):
        for path in ("inbox", "accounts", "tasks", "calendar"):
            self.assertEqual(self.client.get(f"/api/{path}").status_code, 200)

    def start_until_approval(self):
        workflow_id = "executive-customer-review"
        started = self.client.post(f"/api/workflows/{workflow_id}/start").json()
        self.assertEqual(started["status"], "PLANNING")
        snapshots = []
        for _ in range(10):
            current = self.client.get(f"/api/workflows/{workflow_id}/events").json()["workflow"]
            snapshots.append(current)
        self.assertEqual(current["status"], "AWAITING_APPROVAL")
        self.assertEqual([step["id"] for step in current["steps"][:9] if step["status"] == "COMPLETED"], [step["id"] for step in current["steps"][:9]])
        self.assertEqual(current["steps"][9]["status"], "RUNNING")
        return current, snapshots

    def test_approval_completes_and_generates_report(self):
        current, _ = self.start_until_approval()
        approved = self.client.post(f"/api/workflows/{current['id']}/approve").json()
        self.assertEqual(approved["status"], "RUNNING")
        for _ in range(3):
            approved = self.client.get(f"/api/workflows/{current['id']}/events").json()["workflow"]
        self.assertEqual(approved["status"], "COMPLETED")
        self.assertEqual(approved["report"]["customerAtRisk"], "Acme Health")
        self.assertEqual(approved["report"]["verificationScore"], 96)
        self.assertEqual(approved["reasoning"]["riskScore"], 92)
        self.assertEqual(approved["artifactStorage"]["mode"], "Local")
        self.assertEqual(set(approved["artifactStorage"]["locations"]), {"json", "markdown"})

    def test_rejection_stops_calendar_action(self):
        current, _ = self.start_until_approval()
        rejected = self.client.post(f"/api/workflows/{current['id']}/reject").json()
        self.assertEqual(rejected["status"], "FAILED")
        self.assertEqual(rejected["steps"][10]["status"], "IDLE")
        self.assertIsNone(rejected["report"])

    def test_cancel_and_reset_restore_idle_state(self):
        workflow_id = "executive-customer-review"
        self.client.post(f"/api/workflows/{workflow_id}/start")
        cancelled = self.client.post(f"/api/workflows/{workflow_id}/cancel").json()
        self.assertEqual(cancelled["status"], "CANCELLED")
        reset = self.client.post("/api/workflows/demo").json()
        self.assertEqual(reset["status"], "IDLE")
        self.assertTrue(all(step["status"] == "IDLE" for step in reset["steps"]))

    def test_execution_mode_fallbacks(self):
        keys = {"HCOMPANY_API_KEY": "", "NVIDIA_API_KEY": "", "AWS_S3_BUCKET": ""}
        with patch.dict(os.environ, keys | {"ENTERPRISEOS_MODE": "LIVE"}, clear=False):
            self.assertEqual(api.execution_mode()["resolved"], "DEMO")
        with patch.dict(os.environ, keys | {"ENTERPRISEOS_MODE": "LIVE", "NVIDIA_API_KEY": "configured", "NVIDIA_MOCK_MODE": "false"}, clear=False):
            self.assertEqual(api.execution_mode()["resolved"], "HYBRID")
        with patch.dict(os.environ, {"ENTERPRISEOS_MODE": "LIVE", "HCOMPANY_API_KEY": "configured", "HCOMPANY_MOCK_MODE": "false", "NVIDIA_API_KEY": "configured", "NVIDIA_MOCK_MODE": "false", "AWS_S3_BUCKET": "configured", "AWS_USE_LOCAL_MODE": "false"}, clear=False):
            self.assertEqual(api.execution_mode()["resolved"], "LIVE")

    def test_initialize_workflow(self):
        workflow_id = "executive-customer-review"
        goal = "Draft an executive summary and notify Priya"
        initialized = self.client.post(f"/api/workflows/{workflow_id}/initialize", json={"goal": goal}).json()
        self.assertEqual(initialized["goal"], goal)
        self.assertEqual(initialized["status"], "IDLE")
        self.assertTrue(len(initialized["steps"]) >= 3)

    def test_custom_steps_and_nonstandard_approval_id(self):
        custom_steps = [
            {"id": "review-account", "title": "Review account", "description": "Inspect risk", "status": "IDLE", "application": "CRM", "riskLevel": "high", "requiresApproval": False, "startedAt": None, "completedAt": None, "output": None, "error": None},
            {"id": "approve-custom-action", "title": "Approve action", "description": "Human review", "status": "IDLE", "application": "Approval", "riskLevel": "critical", "requiresApproval": True, "startedAt": None, "completedAt": None, "output": None, "error": None},
            {"id": "custom-report", "title": "Create report", "description": "Publish result", "status": "IDLE", "application": "Executive Report", "riskLevel": "medium", "requiresApproval": False, "startedAt": None, "completedAt": None, "output": None, "error": None},
        ]
        workflow = api.new_workflow(goal="Review a custom account", steps=custom_steps, name="Custom review")
        api.store_workflow(workflow)
        self.assertEqual([step["id"] for step in api.load_workflow(api.WORKFLOW_ID)["steps"]], [step["id"] for step in custom_steps])
        self.client.post(f"/api/workflows/{api.WORKFLOW_ID}/start")
        self.client.get(f"/api/workflows/{api.WORKFLOW_ID}/events")
        paused = self.client.get(f"/api/workflows/{api.WORKFLOW_ID}/events").json()["workflow"]
        self.assertEqual(paused["status"], "AWAITING_APPROVAL")
        approved = self.client.post(f"/api/workflows/{api.WORKFLOW_ID}/approve").json()
        self.assertEqual(approved["steps"][1]["status"], "COMPLETED")
        completed = self.client.get(f"/api/workflows/{api.WORKFLOW_ID}/events").json()["workflow"]
        self.assertEqual(completed["status"], "COMPLETED")

if __name__ == "__main__": unittest.main()
