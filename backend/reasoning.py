"""Validated NVIDIA reasoning with deterministic, non-throwing fallback."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from typing import Any, Callable

import httpx


@dataclass(frozen=True)
class NVIDIAConfig:
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "meta/llama-3.1-70b-instruct"
    timeout_seconds: float = 30.0
    mock_mode: bool = True

    @classmethod
    def from_env(cls):
        return cls(api_key=os.getenv("NVIDIA_API_KEY", ""), base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"), model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct"), timeout_seconds=float(os.getenv("NVIDIA_TIMEOUT_SECONDS", "30")), mock_mode=os.getenv("NVIDIA_MOCK_MODE", "true").lower() not in ("false", "0", "no"))


class AIReasoningProvider(ABC):
    mode = "Unavailable"
    @abstractmethod
    def plan_execution_steps(self, goal: str) -> list[dict[str, Any]]: ...
    @abstractmethod
    def analyze_customer_risk(self, customer: dict[str, Any], feedback: list[dict[str, Any]]) -> dict[str, Any]: ...
    @abstractmethod
    def summarize_engineering_issues(self, issues: list[dict[str, Any]]) -> dict[str, Any]: ...
    @abstractmethod
    def generate_action_plan(self, context: dict[str, Any]) -> list[dict[str, Any]]: ...
    @abstractmethod
    def draft_customer_response(self, context: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def verify_workflow_result(self, result: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...


RISK = {"customerName": "Acme Health", "riskScore": 92, "riskLevel": "Critical", "reasons": ["Recurring payment timeouts affect patient billing", "Claims export inaccuracies reduced finance confidence", "Renewal decision is 42 days away", "Three open account issues"], "businessImpact": "$640,000 renewal is at immediate risk; ongoing defects may trigger executive escalation and competitive review."}
ISSUES = {"summary": "Three Acme Health engineering issues directly support the escalation.", "issues": [{"title": "Payment processing timeout", "status": "Blocked", "severity": "Critical"}, {"title": "Claims export rounding", "status": "In progress", "severity": "High"}, {"title": "Customer-facing incident RCA", "status": "In progress", "severity": "High"}]}
ACTIONS = [{"priority": 1, "action": "Assign a QA owner and validate the payment timeout hotfix", "owner": "Nina Shah", "deadline": "Today, 3:00 PM", "expectedOutcome": "Payment processing stability confirmed before the executive review"}, {"priority": 2, "action": "Validate and deliver a corrected claims export", "owner": "Leo Wong", "deadline": "Tuesday, 12:00 PM", "expectedOutcome": "Acme Finance regains confidence in reported totals"}, {"priority": 3, "action": "Prepare incident RCA and renewal protection options", "owner": "Priya Raman", "deadline": "Before Monday review", "expectedOutcome": "Clear accountability and a protected renewal path"}]
DRAFT = {"subject": "Acme Health remediation and executive review", "body": "Maya, thank you for escalating this. We understand the impact the payment timeouts and reporting discrepancies are having on your team. We have assigned executive and engineering owners, are prioritizing timeout validation today, and will share a verified remediation plan and incident summary in our Monday review.", "tone": "Accountable and action-oriented"}
VERIFY = {"verified": True, "confidence": 0.96, "explanation": "Customer, contract, renewal, issue, action, response, and meeting evidence agree across the source records.", "missingEvidence": []}


def validate_plan_steps(value):
    keys = ("id", "title", "description", "application", "riskLevel", "requiresApproval")
    if not isinstance(value, list) or len(value) < 3 or not all(isinstance(item, dict) and all(key in item for key in keys) for item in value): return False
    if len({item["id"] for item in value}) != len(value): return False
    if not all(item["application"] in ("Inbox", "CRM", "Task Tracker", "Calendar", "Reasoning", "Composer", "Approval", "Executive Report") and item["riskLevel"] in ("low", "medium", "high", "critical") and isinstance(item["requiresApproval"], bool) for item in value): return False
    approval_indexes = [index for index, item in enumerate(value) if item["requiresApproval"]]
    calendar_indexes = [index for index, item in enumerate(value) if item["application"] == "Calendar"]
    return bool(approval_indexes) and (not calendar_indexes or min(approval_indexes) < min(calendar_indexes))
def validate_risk(value):
    required = ("customerName", "riskScore", "riskLevel", "reasons", "businessImpact")
    return isinstance(value, dict) and all(key in value for key in required) and isinstance(value["riskScore"], int) and 0 <= value["riskScore"] <= 100 and isinstance(value["reasons"], list)
def validate_actions(value):
    keys = ("priority", "action", "owner", "deadline", "expectedOutcome")
    return isinstance(value, list) and bool(value) and all(isinstance(item, dict) and all(key in item for key in keys) for item in value)
def validate_verification(value):
    return isinstance(value, dict) and isinstance(value.get("verified"), bool) and isinstance(value.get("confidence"), (int, float)) and 0 <= value["confidence"] <= 1 and isinstance(value.get("explanation"), str) and isinstance(value.get("missingEvidence"), list)
def validate_issues(value): return isinstance(value, dict) and isinstance(value.get("summary"), str) and isinstance(value.get("issues"), list)
def validate_draft(value): return isinstance(value, dict) and all(isinstance(value.get(key), str) for key in ("subject", "body", "tone"))


class DeterministicReasoningProvider(AIReasoningProvider):
    mode = "Mock"
    def plan_execution_steps(self, goal: str):
        return [
            {"id": "open-inbox", "title": "Open Inbox", "description": "Scan communications...", "application": "Inbox", "riskLevel": "low", "requiresApproval": False},
            {"id": "review-escalations", "title": "Review escalations", "description": "Identify critical complaints...", "application": "Inbox", "riskLevel": "medium", "requiresApproval": False},
            {"id": "identify-customer", "title": "Identify affected customer", "description": "Determine risk context...", "application": "Inbox", "riskLevel": "medium", "requiresApproval": False},
            {"id": "open-crm", "title": "Open CRM", "description": "Check accounts...", "application": "CRM", "riskLevel": "low", "requiresApproval": False},
            {"id": "inspect-account", "title": "Inspect account health", "description": "Verify contract size...", "application": "CRM", "riskLevel": "high", "requiresApproval": False},
            {"id": "open-tasks", "title": "Open Task Tracker", "description": "Find engineering items...", "application": "Task Tracker", "riskLevel": "low", "requiresApproval": False},
            {"id": "find-issues", "title": "Find related engineering issues", "description": "Link issues...", "application": "Task Tracker", "riskLevel": "high", "requiresApproval": False},
            {"id": "recommend-actions", "title": "Generate recommended actions", "description": "Formulate plan...", "application": "Reasoning", "riskLevel": "high", "requiresApproval": False},
            {"id": "draft-response", "title": "Draft customer response", "description": "Write response...", "application": "Composer", "riskLevel": "high", "requiresApproval": False},
            {"id": "human-approval", "title": "Request human approval", "description": "Hold for review...", "application": "Approval", "riskLevel": "critical", "requiresApproval": True},
            {"id": "open-calendar", "title": "Open Calendar", "description": "Look for slots...", "application": "Calendar", "riskLevel": "medium", "requiresApproval": False},
            {"id": "prepare-meeting", "title": "Prepare a review meeting", "description": "Book invite...", "application": "Calendar", "riskLevel": "high", "requiresApproval": False},
            {"id": "generate-report", "title": "Generate executive report", "description": "Compile brief...", "application": "Executive Report", "riskLevel": "medium", "requiresApproval": False},
        ]

    def analyze_customer_risk(self, customer, feedback): return json.loads(json.dumps(RISK))
    def summarize_engineering_issues(self, issues): return json.loads(json.dumps(ISSUES))
    def generate_action_plan(self, context): return json.loads(json.dumps(ACTIONS))
    def draft_customer_response(self, context): return json.loads(json.dumps(DRAFT))
    def verify_workflow_result(self, result): return json.loads(json.dumps(VERIFY))
    def health_check(self): return {"healthy": True, "mode": "Mock", "provider": "DeterministicReasoningProvider", "model": "deterministic"}


class NVIDIAReasoningProvider(AIReasoningProvider):
    mode = "Connected"
    def __init__(self, config: NVIDIAConfig | None = None, client: httpx.Client | None = None, fallback: AIReasoningProvider | None = None):
        self.config = config or NVIDIAConfig.from_env(); self.client = client or httpx.Client(timeout=self.config.timeout_seconds); self.fallback = fallback or DeterministicReasoningProvider(); self.last_fallback_reason = None

    def _request(self, task: str, payload: Any, validator: Callable, fallback: Callable):
        if not self.config.api_key: self.last_fallback_reason = "Missing NVIDIA_API_KEY"; return fallback()
        prompt = f"Task: {task}\nReturn JSON only matching the requested schema.\nInput: {json.dumps(payload)}"
        for attempt in range(2):
            if attempt == 1: prompt = f"Repair the malformed response below. Return valid JSON only.\n{raw}"
            try:
                response = self.client.post(self.config.base_url.rstrip("/") + "/chat/completions", headers={"Authorization": f"Bearer {self.config.api_key}", "Accept": "application/json"}, json={"model": self.config.model, "messages": [{"role": "system", "content": "You produce strictly structured enterprise reasoning as JSON."}, {"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 1200, "stream": False})
                response.raise_for_status(); raw = response.json()["choices"][0]["message"]["content"]; parsed = json.loads(raw) if isinstance(raw, str) else raw
                if validator(parsed): self.last_fallback_reason = None; return parsed
                raw = json.dumps(parsed)
            except httpx.TimeoutException: self.last_fallback_reason = "NVIDIA request timed out"; return fallback()
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc: raw = str(exc)
        self.last_fallback_reason = "Malformed NVIDIA output after one repair attempt"
        return fallback()

    def plan_execution_steps(self, goal: str):
        return self._request(
            "Plan a list of execution steps to accomplish the business goal. Available applications to choose for steps: Inbox, CRM, Task Tracker, Calendar, Composer, Approval, Executive Report. At least one step must be 'Approval' and set requiresApproval=true, which acts as a safety checkpoint before calendar/write operations. Schema: array of steps, each with: id, title, description, application, riskLevel (low/medium/high/critical), requiresApproval boolean.",
            {"goal": goal},
            validate_plan_steps,
            lambda: self.fallback.plan_execution_steps(goal)
        )

    def analyze_customer_risk(self, customer, feedback): return self._request("Analyze customer risk. Schema: customerName, riskScore integer 0-100, riskLevel, reasons array, businessImpact.", {"customer": customer, "feedback": feedback}, validate_risk, lambda: self.fallback.analyze_customer_risk(customer, feedback))
    def summarize_engineering_issues(self, issues): return self._request("Summarize engineering issues. Schema: summary string, issues array.", issues, validate_issues, lambda: self.fallback.summarize_engineering_issues(issues))
    def generate_action_plan(self, context): return self._request("Generate action plan array. Each item: priority, action, owner, deadline, expectedOutcome.", context, validate_actions, lambda: self.fallback.generate_action_plan(context))
    def draft_customer_response(self, context): return self._request("Draft customer response. Schema: subject, body, tone.", context, validate_draft, lambda: self.fallback.draft_customer_response(context))
    def verify_workflow_result(self, result): return self._request("Verify workflow result. Schema: verified boolean, confidence 0-1, explanation, missingEvidence array.", result, validate_verification, lambda: self.fallback.verify_workflow_result(result))
    def health_check(self):
        if not self.config.api_key: return {"healthy": False, "mode": "Unavailable", "provider": "NVIDIAReasoningProvider", "model": self.config.model, "error": "Missing API key"}
        return {"healthy": True, "mode": "Configured", "provider": "NVIDIAReasoningProvider", "model": self.config.model}


def configured_reasoning_provider(config: NVIDIAConfig | None = None, execution_mode: str | None = None):
    config = config or NVIDIAConfig.from_env()
    return DeterministicReasoningProvider() if execution_mode == "DEMO" or config.mock_mode else NVIDIAReasoningProvider(config)
