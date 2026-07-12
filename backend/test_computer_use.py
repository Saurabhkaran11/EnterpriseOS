import unittest

from computer_use import (
    ActionLimitError,
    BrowserGoal,
    ComputerUseConfig,
    FallbackComputerUseProvider,
    HCompanyComputerUseProvider,
    InvalidProviderResponseError,
    MockComputerUseProvider,
    NavigationBlockedError,
    ProviderTimeoutError,
    SensitiveActionBlockedError,
    enforce_sensitive_action,
    validate_url,
)


def goal(**changes):
    values = dict(objective="Inspect Acme Health and stop before meeting confirmation", starting_url="http://localhost:3000", allowed_urls=["http://localhost:3000", "http://127.0.0.1:3000"], expected_result="Account risk and issues", maximum_actions=12, timeout=30, sensitive_action_restrictions=["send email", "purchase", "delete", "confirm meeting"])
    values.update(changes)
    return BrowserGoal(**values)


class ComputerUseProviderTest(unittest.TestCase):
    def test_missing_api_key(self):
        provider = HCompanyComputerUseProvider(ComputerUseConfig(api_key="", mock_mode=False))
        self.assertFalse(provider.health_check()["healthy"])
        with self.assertRaisesRegex(RuntimeError, "HCOMPANY_API_KEY"):
            provider.plan_action("test", {})

    def test_provider_timeout(self):
        with self.assertRaises(ProviderTimeoutError):
            MockComputerUseProvider().execute_browser_goal(goal(timeout=-1))

    def test_invalid_provider_response(self):
        provider = HCompanyComputerUseProvider(ComputerUseConfig(api_key="test", mock_mode=False), lambda _: {"unexpected": True})
        with self.assertRaises(InvalidProviderResponseError):
            provider.execute_browser_goal(goal())

    def test_agent_platform_session_lifecycle(self):
        def bridge(payload):
            if payload["operation"] == "start": return {"id": "session-1", "status": "pending", "agentViewUrl": "https://platform.hcompany.ai/session-1"}
            if payload["operation"] == "status": return {"id": "session-1", "status": "completed", "steps": 4, "answer": "Acme Health is at risk"}
            return {"id": "session-1", "status": "interrupted"}
        provider = HCompanyComputerUseProvider(ComputerUseConfig(api_key="test", mock_mode=False), bridge)
        started = provider.execute_browser_goal(goal())
        self.assertEqual(started["providerMode"], "Connected")
        self.assertEqual(provider.get_status(started["executionId"])["executionStatus"], "COMPLETED")
        self.assertEqual(provider.cancel_execution(started["executionId"])["executionStatus"], "CANCELLED")

    def test_navigation_outside_allowed_domain(self):
        with self.assertRaises(NavigationBlockedError):
            validate_url("https://evil.example/steal", ["http://localhost:3000"])
        with self.assertRaises(NavigationBlockedError):
            validate_url("https://evil.example/steal", ["https://evil.example"], "demo.enterpriseos.test")

    def test_maximum_action_limit(self):
        provider = MockComputerUseProvider(ComputerUseConfig(max_actions=1))
        with self.assertRaises(ActionLimitError):
            provider.execute_browser_goal(goal(maximum_actions=5))

    def test_mock_fallback(self):
        config = ComputerUseConfig(api_key="", mock_mode=False)
        provider = FallbackComputerUseProvider(HCompanyComputerUseProvider(config), MockComputerUseProvider(config))
        result = provider.execute_browser_goal(goal())
        self.assertEqual(result["providerMode"], "Mock")
        self.assertEqual(result["executionStatus"], "AWAITING_APPROVAL")
        self.assertIn("HCOMPANY_API_KEY", result["fallbackReason"])

    def test_sensitive_actions_blocked(self):
        for action in ("Send email to customer", "Purchase credits", "Delete account", "Confirm meeting"):
            with self.subTest(action=action), self.assertRaises(SensitiveActionBlockedError):
                enforce_sensitive_action(action, [])
        enforce_sensitive_action("Stop before confirming meeting", ["confirm meeting"])

    def test_complete_mock_script(self):
        result = MockComputerUseProvider().execute_browser_goal(goal())
        self.assertEqual(len(result["actionsTaken"]), 10)
        self.assertEqual(result["currentUrl"], "http://localhost:3000/workspace/calendar")
        self.assertIn("Meeting not confirmed", result["extractedInformation"][-1])
        self.assertEqual(result["executionStatus"], "AWAITING_APPROVAL")


if __name__ == "__main__": unittest.main()
