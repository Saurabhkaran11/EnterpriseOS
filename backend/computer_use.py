"""Isolated H Company computer-use provider layer.

The real provider delegates hosted browser sessions to H Company's official
``hai-agents`` SDK through a small JSON/stdin bridge. The mock stays available
for localhost demos and provider failures.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.parse import urlparse

BLOCKED_ACTIONS = ("send email", "send message", "purchase", "buy", "delete", "confirm meeting", "book meeting", "schedule meeting")


class ComputerUseError(RuntimeError): pass
class ProviderTimeoutError(ComputerUseError): pass
class InvalidProviderResponseError(ComputerUseError): pass
class NavigationBlockedError(ComputerUseError): pass
class ActionLimitError(ComputerUseError): pass
class SensitiveActionBlockedError(ComputerUseError): pass


@dataclass(frozen=True)
class ComputerUseConfig:
    api_key: str = ""
    base_url: str = "https://agp.hcompany.ai"
    model: str = "h/web-surfer-pro"
    timeout_seconds: float = 30.0
    mock_mode: bool = True
    max_actions: int = 12
    demo_domain: str = "localhost"

    @classmethod
    def from_env(cls):
        public_url = os.getenv("ENTERPRISEOS_PUBLIC_URL", "")
        public_host = urlparse(public_url).hostname if public_url else None
        return cls(
            api_key=os.getenv("HAI_API_KEY") or os.getenv("HCOMPANY_API_KEY", ""),
            base_url=os.getenv("HCOMPANY_BASE_URL", "https://agp.hcompany.ai"),
            model=os.getenv("HCOMPANY_MODEL", "h/web-surfer-pro"),
            timeout_seconds=float(os.getenv("HCOMPANY_TIMEOUT_SECONDS", "30")),
            mock_mode=os.getenv("HCOMPANY_MOCK_MODE", "true").lower() not in ("false", "0", "no"),
            max_actions=int(os.getenv("HCOMPANY_MAX_ACTIONS", "12")),
            demo_domain=os.getenv("ENTERPRISEOS_DEMO_DOMAIN", public_host or "localhost"),
        )


@dataclass
class BrowserGoal:
    objective: str
    starting_url: str
    allowed_urls: list[str]
    expected_result: str
    maximum_actions: int
    timeout: float
    sensitive_action_restrictions: list[str]


def validate_url(url: str, allowed_urls: list[str], demo_domain: str = "localhost"):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise NavigationBlockedError("Only HTTP(S) navigation is allowed")
    allowed_hosts = {urlparse(item).hostname for item in allowed_urls}
    if parsed.hostname not in allowed_hosts or parsed.hostname not in ("localhost", "127.0.0.1", demo_domain):
        raise NavigationBlockedError(f"Navigation outside the allowed domain was blocked: {parsed.hostname}")


def enforce_sensitive_action(action: str, restrictions: list[str]):
    normalized = action.lower()
    if normalized.startswith("stop before"):
        return
    denied = tuple(item.lower() for item in restrictions) + BLOCKED_ACTIONS
    if any(item in normalized for item in denied):
        raise SensitiveActionBlockedError(f"Sensitive action blocked: {action}")


class ComputerUseProvider(ABC):
    mode = "Unavailable"
    @abstractmethod
    def plan_action(self, objective: str, observation: dict[str, Any]) -> dict[str, Any]: ...
    @abstractmethod
    def execute_browser_goal(self, goal: BrowserGoal) -> dict[str, Any]: ...
    @abstractmethod
    def get_status(self, execution_id: str) -> dict[str, Any]: ...
    @abstractmethod
    def cancel_execution(self, execution_id: str) -> dict[str, Any]: ...
    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...


SCRIPT = [
    ("Open Inbox", "/workspace/inbox", "Inbox opened", None),
    ("Select Acme Health escalation", "/workspace/inbox", "Urgent payment-failure escalation selected", "Acme Health — recurring payment timeouts affecting patients"),
    ("Extract customer and issue", "/workspace/inbox", "Customer and issue extracted", "Acme Health; payment timeouts and inaccurate claims exports"),
    ("Open CRM", "/workspace/crm", "CRM opened", None),
    ("Locate Acme Health", "/workspace/crm", "Acme Health account highlighted", "$640,000 contract; health: at risk"),
    ("Read value and health", "/workspace/crm", "Commercial risk captured", "$640,000; at risk; renewal August 23; 3 open issues"),
    ("Open Task Tracker", "/workspace/tasks", "Task Tracker opened", None),
    ("Locate related issues", "/workspace/tasks", "Three related issues highlighted", "Payment timeout blocked; claims export and RCA in progress"),
    ("Open Calendar", "/workspace/calendar", "Calendar opened", "Monday 9:00 AM executive review is available"),
    ("Stop before confirming meeting", "/workspace/calendar", "Stopped at approval boundary", "Meeting not confirmed; human approval required"),
]


class MockComputerUseProvider(ComputerUseProvider):
    mode = "Mock"
    def __init__(self, config: ComputerUseConfig | None = None):
        self.config = config or ComputerUseConfig()
        self.executions: dict[str, dict[str, Any]] = {}

    def plan_action(self, objective: str, observation: dict[str, Any]):
        index = int(observation.get("action_index", 0))
        limit = min(self.config.max_actions, int(observation.get("maximum_actions", self.config.max_actions)))
        if index >= limit: raise ActionLimitError("Maximum action count reached")
        if index >= len(SCRIPT): return {"status": "completed", "action": "Goal complete", "confidence": 0.98}
        title, path, latest, extracted = SCRIPT[index]
        base = observation.get("base_url", "http://localhost:3000")
        current_url = base.rstrip("/") + path
        validate_url(current_url, observation.get("allowed_urls", [base]), self.config.demo_domain)
        enforce_sensitive_action(title, observation.get("sensitive_action_restrictions", []))
        return {"status": "running" if index < len(SCRIPT)-1 else "awaiting_approval", "action": title, "latestAction": latest, "currentUrl": current_url, "extractedInformation": extracted, "screenshotReference": f"mock://enterpriseos/action-{index+1}", "confidence": round(0.91 + index * .007, 2)}

    def execute_browser_goal(self, goal: BrowserGoal):
        started = time.monotonic(); actions = []; extracted = []
        maximum = min(goal.maximum_actions, self.config.max_actions)
        validate_url(goal.starting_url, goal.allowed_urls, self.config.demo_domain)
        for index in range(len(SCRIPT)):
            if time.monotonic() - started > goal.timeout: raise ProviderTimeoutError("Computer-use execution timed out")
            result = self.plan_action(goal.objective, {"action_index": index, "maximum_actions": maximum, "base_url": goal.starting_url, "allowed_urls": goal.allowed_urls, "sensitive_action_restrictions": goal.sensitive_action_restrictions})
            actions.append(result["action"])
            if result.get("extractedInformation"): extracted.append(result["extractedInformation"])
        execution_id = "hcu-enterpriseos-demo"
        response = {"executionId": execution_id, "executionStatus": "AWAITING_APPROVAL", "actionsTaken": actions, "currentUrl": result["currentUrl"], "extractedInformation": extracted, "screenshots": [f"mock://enterpriseos/action-{i+1}" for i in range(len(actions))], "confidence": result["confidence"], "errorDetails": None, "providerMode": self.mode}
        self.executions[execution_id] = response
        return response

    def get_status(self, execution_id: str): return self.executions.get(execution_id, {"executionId": execution_id, "executionStatus": "IDLE", "providerMode": self.mode})
    def cancel_execution(self, execution_id: str):
        result = self.get_status(execution_id) | {"executionStatus": "CANCELLED"}; self.executions[execution_id] = result; return result
    def health_check(self): return {"healthy": True, "mode": self.mode, "provider": "MockComputerUseProvider"}


class HCompanyComputerUseProvider(ComputerUseProvider):
    mode = "Configured"
    def __init__(self, config: ComputerUseConfig | None = None, bridge_runner=None):
        self.config = config or ComputerUseConfig.from_env()
        self.bridge_runner = bridge_runner or self._run_bridge
        self.executions: dict[str, dict[str, Any]] = {}

    def _require_key(self):
        if not self.config.api_key: raise ComputerUseError("HAI_API_KEY or HCOMPANY_API_KEY is not configured")

    def _run_bridge(self, payload: dict[str, Any]):
        bridge = Path(__file__).resolve().parents[1] / "scripts" / "hcompany-agent-bridge.mjs"
        env = os.environ.copy()
        env["HAI_API_KEY"] = self.config.api_key
        try:
            completed = subprocess.run(
                ["node", str(bridge)], input=json.dumps(payload), text=True,
                capture_output=True, timeout=self.config.timeout_seconds + 5, env=env, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderTimeoutError("H Company Agent Platform request timed out") from exc
        try:
            result = json.loads(completed.stdout)
        except (TypeError, json.JSONDecodeError) as exc:
            raise InvalidProviderResponseError("H Company SDK bridge returned invalid JSON") from exc
        if completed.returncode or result.get("error"):
            raise ComputerUseError(f"H Company Agent Platform request failed: {result.get('error', 'unknown error')}")
        return result

    def plan_action(self, objective: str, observation: dict[str, Any]):
        self._require_key()
        # The Agent Platform owns the browser loop. Keep the dashboard preview
        # deterministic until execute_browser_goal starts a genuine session.
        return MockComputerUseProvider(self.config).plan_action(objective, observation) | {"providerMode": "Configured"}

    def execute_browser_goal(self, goal: BrowserGoal):
        self._require_key(); validate_url(goal.starting_url, goal.allowed_urls, self.config.demo_domain)
        restrictions = "; ".join(goal.sensitive_action_restrictions + ["never leave the allowed domains"])
        objective = f"{goal.objective}\nExpected result: {goal.expected_result}.\nSafety: {restrictions}. Stop before any sensitive action."
        result = self.bridge_runner({"operation": "start", "baseUrl": self.config.base_url, "model": self.config.model, "objective": objective, "startingUrl": goal.starting_url, "maxActions": min(goal.maximum_actions, self.config.max_actions), "timeoutSeconds": min(goal.timeout, self.config.timeout_seconds)})
        if not isinstance(result, dict) or not result.get("id"):
            raise InvalidProviderResponseError("H Company returned an invalid session response")
        execution_id = result["id"]
        response = {
            "executionId": execution_id,
            "executionStatus": str(result.get("status", "pending")).upper(),
            "actionsTaken": [], "currentUrl": goal.starting_url,
            "extractedInformation": [], "screenshots": [], "confidence": None,
            "errorDetails": None,
            "providerMode": "Connected", "agentViewUrl": result.get("agentViewUrl"),
        }
        self.executions[execution_id] = response
        return response
    def get_status(self, execution_id: str):
        self._require_key()
        result = self.bridge_runner({"operation": "status", "baseUrl": self.config.base_url, "executionId": execution_id})
        if not isinstance(result, dict) or not result.get("status"):
            raise InvalidProviderResponseError("H Company returned an invalid status response")
        return {"executionId": execution_id, "executionStatus": result["status"].upper(), "actionsTaken": result.get("steps", 0), "extractedInformation": result.get("answer"), "confidence": None, "errorDetails": result.get("error"), "providerMode": "Connected", "agentViewUrl": result.get("agentViewUrl"), "outcome": result.get("outcome")}
    def cancel_execution(self, execution_id: str):
        self._require_key(); self.bridge_runner({"operation": "cancel", "baseUrl": self.config.base_url, "executionId": execution_id})
        return {"executionId": execution_id, "executionStatus": "CANCELLED", "providerMode": "Connected"}
    def health_check(self):
        if not self.config.api_key: return {"healthy": False, "mode": "Unavailable", "provider": "HCompanyComputerUseProvider", "error": "Missing API key"}
        return {"healthy": True, "mode": "Configured", "provider": "HCompanyComputerUseProvider"}


class FallbackComputerUseProvider(ComputerUseProvider):
    def __init__(self, primary: ComputerUseProvider, fallback: MockComputerUseProvider): self.primary, self.fallback = primary, fallback
    @property
    def mode(self): return self.primary.health_check().get("mode") if self.primary.health_check().get("healthy") else "Mock"
    def plan_action(self, objective, observation):
        try: return self.primary.plan_action(objective, observation) | {"providerMode": self.primary.mode}
        except ComputerUseError as exc: return self.fallback.plan_action(objective, observation) | {"providerMode": "Mock", "fallbackReason": str(exc)}
    def execute_browser_goal(self, goal):
        try: return self.primary.execute_browser_goal(goal)
        except ComputerUseError as exc: return self.fallback.execute_browser_goal(goal) | {"fallbackReason": str(exc), "providerMode": "Mock"}
    def get_status(self, execution_id): return self.primary.get_status(execution_id)
    def cancel_execution(self, execution_id): return self.primary.cancel_execution(execution_id)
    def health_check(self): return {"healthy": True, "mode": self.mode, "primary": self.primary.health_check(), "fallback": self.fallback.health_check()}


def configured_provider(config: ComputerUseConfig | None = None, execution_mode: str | None = None):
    config = config or ComputerUseConfig.from_env()
    mock = MockComputerUseProvider(config)
    if execution_mode == "DEMO" or config.mock_mode: return mock
    return FallbackComputerUseProvider(HCompanyComputerUseProvider(config), mock)
